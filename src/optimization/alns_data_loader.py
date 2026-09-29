from __future__ import annotations

import sqlite3
from pathlib import Path

from src.optimization.alns_solution import ALNSSolution, TimetableRecord


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "data" / "database" / "railway_recovery.db"


class ALNSDataLoader:
    """Load timetable data from SQLite into an ALNS solution."""

    def __init__(self, database_path: Path = DATABASE_PATH) -> None:
        self.database_path = database_path

    def load_timetable(self) -> ALNSSolution:
        """Load the complete timetable into an ALNS solution."""

        if not self.database_path.exists():
            raise FileNotFoundError(
                f"Database not found: {self.database_path}"
            )

        solution = ALNSSolution()

        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row

        try:
            rows = connection.execute(
                """
                SELECT
                    timetable_record_id,
                    train_number,
                    station_code,
                    day,
                    stop_number,
                    arrival,
                    departure,
                    resource_id,
                    platform_number,
                    platform_type
                FROM timetable
                ORDER BY train_number, day, stop_number
                """
            ).fetchall()

            for row in rows:
                record = TimetableRecord(
                    timetable_record_id=row["timetable_record_id"],
                    train_number=row["train_number"],
                    station_code=row["station_code"],
                    day=row["day"],
                    stop_number=row["stop_number"],
                    arrival=row["arrival"],
                    departure=row["departure"],
                    resource_id=row["resource_id"],
                    platform_number=row["platform_number"],
                    platform_type=row["platform_type"],
                )

                solution.add_record(record)

        finally:
            connection.close()

        return solution


def load_initial_solution(
    database_path: Path = DATABASE_PATH,
) -> ALNSSolution:
    """Convenience function for loading the initial ALNS solution."""

    loader = ALNSDataLoader(database_path)
    return loader.load_timetable()


if __name__ == "__main__":
    solution = load_initial_solution()

    print("ALNS timetable loader test")
    print("--------------------------")
    print(f"Database: {DATABASE_PATH}")
    print(f"Timetable records loaded: {solution.record_count()}")

    if solution.record_count() > 0:
        first_record = next(iter(solution.records.values()))

        print("\nFirst record:")
        print(f"  ID: {first_record.timetable_record_id}")
        print(f"  Train: {first_record.train_number}")
        print(f"  Station: {first_record.station_code}")
        print(f"  Day: {first_record.day}")
        print(f"  Stop: {first_record.stop_number}")
        print(f"  Arrival: {first_record.arrival}")
        print(f"  Departure: {first_record.departure}")
        print(f"  Resource: {first_record.resource_id}")
        print(f"  Platform: {first_record.platform_number}")