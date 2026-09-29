from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from src.optimization.alns_allocation import (
    CandidateAllocationCalculator,
)
from src.optimization.alns_candidate import CandidateBuilder
from src.optimization.alns_data_loader import (
    load_initial_solution,
)
from src.optimization.alns_disruption import (
    Disruption,
    DisruptionFilter,
)
from src.optimization.alns_feasibility import (
    FeasibilityChecker,
)
from src.optimization.alns_move import (
    TimetableModification,
)
from src.optimization.alns_solution import (
    ALNSSolution,
    TimetableRecord,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "database"
    / "railway_recovery.db"
)


# In this project:
# EMU and MEMU are suburban trains.
# All other train types are treated as mainline trains.
SUBURBAN_TRAIN_TYPES = {
    "EMU",
    "MEMU",
}


MIN_RECOVERY_BUFFER_MINUTES = 5


@dataclass
class RepairCandidate:
    """Represents one feasible timetable repair."""

    timetable_record_id: int
    train_number: str
    station_code: str
    original_resource_id: str
    alternative_resource_id: str
    alternative_platform_number: int
    alternative_platform_type: str
    buffer_minutes: int
    reason: str


class ALNSRepairOperator:
    """
    Generate feasible platform reassignment repairs
    for timetable records affected by a disruption.

    Platform compatibility:

    EMU / MEMU:
        MAINLINE -> allowed
        SUBURBAN -> allowed

    All other train types:
        MAINLINE -> allowed
        SUBURBAN -> not allowed
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

        self.candidate_builder = CandidateBuilder()

        self.feasibility_checker = FeasibilityChecker(
            db_path
        )

        self.allocation_calculator = (
            CandidateAllocationCalculator()
        )

    def get_train_type(
        self,
        train_number: str,
    ) -> str:
        """Return the train type from the trains table."""

        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT train_type
                FROM trains
                WHERE train_number = ?
                """,
                (train_number,),
            ).fetchone()

        if row is None:
            raise ValueError(
                f"Train {train_number} was not found "
                f"in the trains table."
            )

        return row[0]

    def is_platform_compatible(
        self,
        train_type: str,
        platform_type: str,
    ) -> bool:
        """
        Check whether a train can use a platform.

        Rules:

        - Every train type can use MAINLINE.
        - EMU and MEMU can use SUBURBAN.
        - Other train types cannot use SUBURBAN.
        """

        normalized_train_type = (
            train_type.strip().upper()
        )

        normalized_platform_type = (
            platform_type.strip().upper()
        )

        if normalized_platform_type == "MAINLINE":
            return True

        if normalized_platform_type == "SUBURBAN":
            return (
                normalized_train_type
                in SUBURBAN_TRAIN_TYPES
            )

        return False

    def get_alternative_platforms(
        self,
        record: TimetableRecord,
    ) -> list[dict]:
        """
        Return compatible alternative platforms
        at the same station.
        """

        train_type = self.get_train_type(
            record.train_number
        )

        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row

            rows = connection.execute(
                """
                SELECT
                    resource_id,
                    platform_number,
                    platform_type
                FROM platforms
                WHERE station_code = ?
                  AND resource_type = 'PLATFORM'
                  AND resource_id != ?
                ORDER BY platform_number
                """,
                (
                    record.station_code,
                    record.resource_id,
                ),
            ).fetchall()

        compatible_platforms = []

        for row in rows:
            platform_type = row["platform_type"]

            if not self.is_platform_compatible(
                train_type,
                platform_type,
            ):
                continue

            compatible_platforms.append(
                {
                    "resource_id": row["resource_id"],
                    "platform_number": row[
                        "platform_number"
                    ],
                    "platform_type": platform_type,
                }
            )

        return compatible_platforms

    def generate_repairs_for_record(
        self,
        solution: ALNSSolution,
        record: TimetableRecord,
        disruption: Disruption,
    ) -> list[RepairCandidate]:
        """
        Generate feasible repairs for one affected
        timetable record.
        """

        # The record must be at the disrupted station.
        if (
            record.station_code
            != disruption.station_code
        ):
            return []

        # The record must currently use the
        # disrupted resource.
        if (
            record.resource_id
            != disruption.resource_id
        ):
            return []

        train_type = self.get_train_type(
            record.train_number
        )

        alternative_platforms = (
            self.get_alternative_platforms(record)
        )

        repairs: list[RepairCandidate] = []

        for platform in alternative_platforms:

            alternative_resource_id = (
                platform["resource_id"]
            )

            alternative_platform_number = (
                platform["platform_number"]
            )

            alternative_platform_type = (
                platform["platform_type"]
            )

            # Final compatibility safety check.
            if not self.is_platform_compatible(
                train_type,
                alternative_platform_type,
            ):
                continue

            modification = TimetableModification(
                timetable_record_id=(
                    record.timetable_record_id
                ),
                new_resource_id=(
                    alternative_resource_id
                ),
                new_platform_number=(
                    alternative_platform_number
                ),
                new_platform_type=(
                    alternative_platform_type
                ),
                reason=(
                    f"Reassign train "
                    f"{record.train_number} from "
                    f"{record.resource_id} to "
                    f"{alternative_resource_id}"
                ),
            )

            # Create an independent ALNS candidate.
            candidate = (
                self.candidate_builder.apply_modification(
                    solution,
                    modification,
                )
            )

            candidate_record = candidate.get_record(
                record.timetable_record_id
            )

            if candidate_record is None:
                continue

            # Check the modified record against
            # the modified candidate solution.
            #
            # check_record() returns:
            #
            #     (is_feasible, violations)
            #
            # We must unpack the tuple because a non-empty
            # tuple is True in Python even when is_feasible
            # itself is False.
            is_feasible, violations = (
                self.feasibility_checker.check_record(
                    candidate_record,
                    candidate,
                )
            )

            if not is_feasible:
                continue

            # Calculate the candidate allocation.
            #
            # The project minimum recovery buffer is
            # 5 minutes.
            #
            # For records with arrival/departure values,
            # calculate() is used.
            if (
                candidate_record.arrival
                and candidate_record.departure
            ):
                candidate_allocation = (
                    self.allocation_calculator.calculate(
                        timetable_record_id=(
                            candidate_record.timetable_record_id
                        ),
                        resource_id=(
                            candidate_record.resource_id
                        ),
                        day=candidate_record.day,
                        arrival=(
                            candidate_record.arrival
                        ),
                        departure=(
                            candidate_record.departure
                        ),
                        buffer_minutes=(
                            MIN_RECOVERY_BUFFER_MINUTES
                        ),
                    )
                )

            else:
                # The timetable record does not contain
                # enough timing information to calculate
                # the allocation directly.
                #
                # The feasibility checker has already
                # validated the candidate.
                candidate_allocation = None

            if candidate_allocation is not None:
                buffer_minutes = (
                    candidate_allocation.buffer_minutes
                )
            else:
                buffer_minutes = (
                    MIN_RECOVERY_BUFFER_MINUTES
                )

            repairs.append(
                RepairCandidate(
                    timetable_record_id=(
                        record.timetable_record_id
                    ),
                    train_number=record.train_number,
                    station_code=record.station_code,
                    original_resource_id=(
                        record.resource_id
                    ),
                    alternative_resource_id=(
                        alternative_resource_id
                    ),
                    alternative_platform_number=(
                        alternative_platform_number
                    ),
                    alternative_platform_type=(
                        alternative_platform_type
                    ),
                    buffer_minutes=buffer_minutes,
                    reason=(
                        f"Compatible {train_type} train "
                        f"reassigned from "
                        f"{record.resource_id} to "
                        f"{alternative_resource_id}"
                    ),
                )
            )

        return repairs

    def generate_repairs(
        self,
        solution: ALNSSolution,
        affected_records: list[TimetableRecord],
        disruption: Disruption,
    ) -> list[RepairCandidate]:
        """Generate repairs for all affected records."""

        all_repairs: list[RepairCandidate] = []

        for record in affected_records:

            repairs = (
                self.generate_repairs_for_record(
                    solution,
                    record,
                    disruption,
                )
            )

            all_repairs.extend(repairs)

        return all_repairs

    def select_repair_candidate(
        self,
        repairs: list[RepairCandidate],
        strategy: str = "standard_repair",
        iteration_index: int = 0,
        record_index: int = 0,
        rng: Any = None,
    ) -> RepairCandidate | None:
        """
        Select a repair candidate from available feasible repairs according to a strategy.
        """
        if not repairs:
            return None

        if strategy == "standard_repair":
            idx = (iteration_index + record_index) % len(repairs) if iteration_index > 0 else 0
            return repairs[idx]
        elif strategy == "max_buffer_repair":
            max_b = max(r.buffer_minutes for r in repairs)
            max_repairs = [r for r in repairs if r.buffer_minutes == max_b]
            idx = (iteration_index + record_index) % len(max_repairs)
            return max_repairs[idx]
        elif strategy == "alternative_order_repair":
            idx = (iteration_index + record_index + 1) % len(repairs)
            return repairs[idx]
        elif strategy == "random_repair":
            import random as rnd
            r = rng if rng is not None else rnd
            return r.choice(repairs)
        else:
            return repairs[0]




def main() -> None:
    """Run a controlled multi-record repair test."""

    db_path = str(DATABASE_PATH)

    # Load the existing timetable.
    solution = load_initial_solution(
        DATABASE_PATH
    )

    # Controlled multi-record disruption.
    disruption = Disruption(
        disruption_type="PLATFORM_CLOSURE",
        station_code="MS",
        resource_id="MS-P9",
        start_time="05:00:00",
        end_time="05:20:00",
        day=1,
    )

    # Find affected timetable records.
    disruption_filter = DisruptionFilter(
        DATABASE_PATH
    )

    affected_records = (
        disruption_filter.find_affected_records(
            disruption,
            solution,
        )
    )

    repair_operator = ALNSRepairOperator(
        db_path
    )

    repairs = repair_operator.generate_repairs(
        solution,
        affected_records,
        disruption,
    )

    print(
        "ALNS multi-record repair operator test"
    )
    print(
        "--------------------------------------"
    )

    print(
        f"Disruption resource : "
        f"{disruption.resource_id}"
    )

    print(
        f"Disruption time     : "
        f"{disruption.start_time} -> "
        f"{disruption.end_time}"
    )

    print(
        f"Affected records    : "
        f"{len(affected_records)}"
    )

    print()

    for record in affected_records:

        train_type = (
            repair_operator.get_train_type(
                record.train_number
            )
        )

        print(
            f"Record "
            f"{record.timetable_record_id}"
        )

        print(
            f"  Train             : "
            f"{record.train_number}"
        )

        print(
            f"  Train type        : "
            f"{train_type}"
        )

        print(
            f"  Station           : "
            f"{record.station_code}"
        )

        print(
            f"  Original resource : "
            f"{record.resource_id}"
        )

        record_repairs = [
            repair
            for repair in repairs
            if (
                repair.timetable_record_id
                == record.timetable_record_id
            )
        ]

        print(
            f"  Feasible repairs  : "
            f"{len(record_repairs)}"
        )

        for repair in record_repairs:

            print(
                f"  -> "
                f"{repair.alternative_resource_id} "
                f"(Platform "
                f"{repair.alternative_platform_number}, "
                f"{repair.alternative_platform_type}) "
                f"| Buffer="
                f"{repair.buffer_minutes} min"
            )

        print()


if __name__ == "__main__":
    main()

