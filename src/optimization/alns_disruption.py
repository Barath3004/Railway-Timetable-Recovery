from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from pathlib import Path

from src.optimization.alns_solution import ALNSSolution, TimetableRecord


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "data" / "database" / "railway_recovery.db"


@dataclass
class Disruption:
    """Represents one railway resource disruption."""

    disruption_type: str
    station_code: str
    resource_id: str
    start_time: str
    end_time: str
    day: int

    def __post_init__(self) -> None:
        """Validate the basic disruption information."""

        allowed_types = {
            "PLATFORM_CLOSURE",
            "TRACK_FAILURE",
            "SIGNAL_FAILURE",
            "PLANNED_MAINTENANCE",
            "OTHER_RESOURCE_DISRUPTION",
        }

        if self.disruption_type not in allowed_types:
            raise ValueError(
                f"Unsupported disruption type: {self.disruption_type}"
            )

        if not self.station_code:
            raise ValueError("station_code cannot be empty")

        if not self.resource_id:
            raise ValueError("resource_id cannot be empty")

        if not self.start_time:
            raise ValueError("start_time cannot be empty")

        if not self.end_time:
            raise ValueError("end_time cannot be empty")

        if self.day < 1:
            raise ValueError("day must be greater than or equal to 1")


class DisruptionFilter:
    """Find timetable records affected by a disruption."""

    def __init__(self, database_path: Path = DATABASE_PATH) -> None:
        self.database_path = database_path

    def find_affected_records(
        self,
        disruption: Disruption,
        solution: ALNSSolution,
    ) -> list[TimetableRecord]:
        """Find timetable records whose resource reservation overlaps the disruption."""

        affected_record_ids = self._find_affected_record_ids(disruption)

        affected_records = []

        for record_id in affected_record_ids:
            if record_id in solution.records:
                affected_records.append(solution.records[record_id])

        affected_records.sort(
            key=lambda record: (
                record.train_number,
                record.stop_number,
            )
        )

        return affected_records

    def _find_affected_record_ids(
        self,
        disruption: Disruption,
    ) -> set[int]:
        """
        Query resource allocations for disruption overlap.

        Resource availability is considered occupied from allocation_start
        until release_time.

        release_time includes the required clearance/buffer after the
        timetable occupancy ends.
        """

        if not self.database_path.exists():
            raise FileNotFoundError(
                f"Database not found: {self.database_path}"
            )

        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row

        try:
            rows = connection.execute(
                """
                SELECT DISTINCT timetable_record_id
                FROM resource_allocations
                WHERE station_code = ?
                  AND resource_id = ?
                  AND day = ?
                  AND allocation_start < ?
                  AND COALESCE(release_time, allocation_end) > ?
                ORDER BY timetable_record_id
                """,
                (
                    disruption.station_code,
                    disruption.resource_id,
                    disruption.day,
                    disruption.end_time,
                    disruption.start_time,
                ),
            ).fetchall()

        finally:
            connection.close()

        return {
            row["timetable_record_id"]
            for row in rows
        }


def run_time_overlap_tests(
    disruption_filter: DisruptionFilter,
) -> None:
    """Run controlled tests against the disruption time-overlap logic."""

    print("\nTime-overlap validation")
    print("-----------------------")

    disruption_start = "15:00:00"
    disruption_end = "16:00:00"

    test_cases = [
        {
            "name": "Before disruption",
            "allocation_start": "13:00:00",
            "allocation_end": "14:00:00",
            "expected": False,
        },
        {
            "name": "Inside disruption",
            "allocation_start": "15:10:00",
            "allocation_end": "15:30:00",
            "expected": True,
        },
        {
            "name": "After disruption",
            "allocation_start": "17:00:00",
            "allocation_end": "18:00:00",
            "expected": False,
        },
        {
            "name": "Crosses disruption start",
            "allocation_start": "14:55:00",
            "allocation_end": "15:20:00",
            "expected": True,
        },
        {
            "name": "Clearance extends into disruption",
            "allocation_start": "14:50:00",
            "allocation_end": "15:00:00",
            "release_time": "15:05:00",
            "expected": True,
        },
        {
            "name": "Clearance ends before disruption",
            "allocation_start": "14:50:00",
            "allocation_end": "15:00:00",
            "release_time": "15:00:00",
            "expected": False,
        },
    ]

    for test in test_cases:
        effective_end = test.get(
            "release_time",
            test["allocation_end"],
        )

        overlaps = (
            test["allocation_start"] < disruption_end
            and effective_end > disruption_start
        )

        status = "PASS" if overlaps == test["expected"] else "FAIL"

        print(
            f"{status} | "
            f"{test['name']} | "
            f"Allocation="
            f"{test['allocation_start']} -> "
            f"{test['allocation_end']} | "
            f"Effective Release={effective_end} | "
            f"Disruption="
            f"{disruption_start} -> "
            f"{disruption_end} | "
            f"Overlap={overlaps}"
        )


if __name__ == "__main__":
    from src.optimization.alns_data_loader import load_initial_solution

    disruption = Disruption(
        disruption_type="PLATFORM_CLOSURE",
        station_code="MAS",
        resource_id="MAS-P4",
        start_time="15:00:00",
        end_time="16:00:00",
        day=1,
    )

    solution = load_initial_solution()

    disruption_filter = DisruptionFilter()

    affected_records = disruption_filter.find_affected_records(
        disruption,
        solution,
    )

    print("ALNS disruption filtering test")
    print("------------------------------")

    print(f"Disruption type : {disruption.disruption_type}")
    print(f"Station         : {disruption.station_code}")
    print(f"Resource        : {disruption.resource_id}")
    print(
        f"Time            : "
        f"{disruption.start_time} -> {disruption.end_time}"
    )
    print(f"Day             : {disruption.day}")

    print(f"\nTotal timetable records loaded : {solution.record_count()}")
    print(f"Affected timetable records     : {len(affected_records)}")

    print("\nAffected records:")

    for record in affected_records:
        print(
            f"  ID={record.timetable_record_id} | "
            f"Train={record.train_number} | "
            f"Station={record.station_code} | "
            f"Stop={record.stop_number} | "
            f"Arrival={record.arrival} | "
            f"Departure={record.departure} | "
            f"Resource={record.resource_id}"
        )

    run_time_overlap_tests(disruption_filter)