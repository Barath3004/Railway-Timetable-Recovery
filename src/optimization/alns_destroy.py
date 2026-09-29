from __future__ import annotations

from dataclasses import dataclass

from src.optimization.alns_disruption import Disruption
from src.optimization.alns_solution import (
    ALNSSolution,
    TimetableRecord,
)


@dataclass
class DestroyedRecord:
    """Information about a timetable record removed by destroy."""

    timetable_record_id: int
    train_number: str
    station_code: str
    original_resource_id: str | None
    original_platform_number: int | None


class ALNSDestroyOperator:
    """
    Destroy operator for disruption-aware ALNS.

    The operator removes the current resource assignment from
    timetable records affected by a disruption.

    The timetable record itself is NOT deleted.

    ALNS works entirely on an in-memory copy of the solution.
    The SQLite database is never modified.
    """

    def destroy_record(
        self,
        solution: ALNSSolution,
        record: TimetableRecord,
    ) -> tuple[ALNSSolution, DestroyedRecord]:
        """
        Remove the resource assignment from one affected record.

        The original solution remains unchanged.
        """

        # Create an independent candidate.
        destroyed_solution = solution.copy()

        # Get the corresponding record from the copied solution.
        destroyed_record = destroyed_solution.get_record(
            record.timetable_record_id
        )

        # Preserve information about the assignment being removed.
        destroyed_info = DestroyedRecord(
            timetable_record_id=(
                destroyed_record.timetable_record_id
            ),
            train_number=destroyed_record.train_number,
            station_code=destroyed_record.station_code,
            original_resource_id=(
                destroyed_record.resource_id
            ),
            original_platform_number=(
                destroyed_record.platform_number
            ),
        )

        # Remove only the resource assignment.
        #
        # The timetable stop itself remains.
        destroyed_record.resource_id = None
        destroyed_record.platform_number = None
        destroyed_record.platform_type = None

        # The candidate must be evaluated again after destruction.
        destroyed_solution.reset_evaluation()

        return destroyed_solution, destroyed_info

    def destroy_records(
        self,
        solution: ALNSSolution,
        records: list[TimetableRecord],
    ) -> tuple[ALNSSolution, list[DestroyedRecord]]:
        """
        Remove resource assignments from multiple affected records.

        All destructions are performed on one independent copy.
        """

        destroyed_solution = solution.copy()
        destroyed_records: list[DestroyedRecord] = []

        for record in records:

            destroyed_record = destroyed_solution.get_record(
                record.timetable_record_id
            )

            destroyed_info = DestroyedRecord(
                timetable_record_id=(
                    destroyed_record.timetable_record_id
                ),
                train_number=destroyed_record.train_number,
                station_code=destroyed_record.station_code,
                original_resource_id=(
                    destroyed_record.resource_id
                ),
                original_platform_number=(
                    destroyed_record.platform_number
                ),
            )

            destroyed_record.resource_id = None
            destroyed_record.platform_number = None
            destroyed_record.platform_type = None

            destroyed_records.append(
                destroyed_info
            )

        destroyed_solution.reset_evaluation()

        return destroyed_solution, destroyed_records

    def destroy_partial(
        self,
        solution: ALNSSolution,
        records: list[TimetableRecord],
        rng: Any = None,
        ratio: float = 0.5,
    ) -> tuple[ALNSSolution, list[DestroyedRecord]]:
        """
        Remove resource assignments from a subset of affected records.

        If only one affected record exists, it destroys that record.
        Otherwise, it destroys a non-empty proper subset of affected records.
        """
        if not records:
            return solution.copy(), []

        if len(records) == 1:
            return self.destroy_records(solution, records)

        import random as rnd
        r = rng if rng is not None else rnd

        k = max(1, min(len(records) - 1, int(round(len(records) * ratio))))
        selected_records = r.sample(records, k)

        return self.destroy_records(solution, selected_records)



def main() -> None:
    """Run a controlled destroy-operator test."""

    from pathlib import Path

    from src.optimization.alns_data_loader import (
        load_initial_solution,
    )
    from src.optimization.alns_disruption import (
        Disruption,
        DisruptionFilter,
    )

    project_root = Path(__file__).resolve().parents[2]

    database_path = (
        project_root
        / "data"
        / "database"
        / "railway_recovery.db"
    )

    # Load the original timetable.
    solution = load_initial_solution(
        database_path
    )

    # Controlled disruption.
    disruption = Disruption(
    disruption_type="PLATFORM_CLOSURE",
    station_code="MS",
    resource_id="MS-P9",
    start_time="05:00:00",
    end_time="05:20:00",
    day=1,
)

    # Find affected records.
    disruption_filter = DisruptionFilter(
        database_path
    )

    affected_records = (
        disruption_filter.find_affected_records(
            disruption,
            solution,
        )
    )

    print(
        "ALNS destroy operator test"
    )
    print(
        "--------------------------"
    )

    print(
        f"Disruption resource : "
        f"{disruption.resource_id}"
    )

    print(
        f"Affected records    : "
        f"{len(affected_records)}"
    )

    print(
        f"Original record count : "
        f"{solution.record_count()}"
    )

    if not affected_records:
        print(
            "\nNo affected records found."
        )
        return

    destroy_operator = ALNSDestroyOperator()

    destroyed_solution, destroyed_records = (
        destroy_operator.destroy_records(
            solution,
            affected_records,
        )
    )

    print()

    for destroyed in destroyed_records:

        original_record = solution.get_record(
            destroyed.timetable_record_id
        )

        destroyed_record = (
            destroyed_solution.get_record(
                destroyed.timetable_record_id
            )
        )

        print(
            f"Record "
            f"{destroyed.timetable_record_id}"
        )

        print(
            f"  Train             : "
            f"{destroyed.train_number}"
        )

        print(
            f"  Station           : "
            f"{destroyed.station_code}"
        )

        print(
            f"  Original resource : "
            f"{destroyed.original_resource_id}"
        )

        print(
            f"  Original platform : "
            f"{destroyed.original_platform_number}"
        )

        print(
            f"  Destroyed resource: "
            f"{destroyed_record.resource_id}"
        )

        print(
            f"  Destroyed platform: "
            f"{destroyed_record.platform_number}"
        )

        print(
            f"  Arrival           : "
            f"{destroyed_record.arrival}"
        )

        print(
            f"  Departure         : "
            f"{destroyed_record.departure}"
        )

        print(
            f"  Original unchanged: "
            f"{'PASS' if original_record.resource_id == destroyed.original_resource_id else 'FAIL'}"
        )

    print()

    print(
        f"Destroyed record count: "
        f"{len(destroyed_records)}"
    )

    print(
        f"Candidate record count: "
        f"{destroyed_solution.record_count()}"
    )

    print(
        f"Record count preserved: "
        f"{'PASS' if solution.record_count() == destroyed_solution.record_count() else 'FAIL'}"
    )

    print(
        f"Candidate evaluation reset: "
        f"{'PASS' if destroyed_solution.objective_value is None else 'FAIL'}"
    )


if __name__ == "__main__":
    main()