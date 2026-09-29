
from __future__ import annotations

import csv
import sqlite3
import tempfile
from pathlib import Path

from src.optimization.alns_candidate import CandidateBuilder
from src.optimization.alns_disruption import Disruption
from src.optimization.alns_evaluation import CandidateEvaluator
from src.optimization.alns_move import TimetableModification
from src.optimization.alns_solution import (
    ALNSSolution,
    TimetableRecord,
)


def create_synthetic_database(db_path: Path) -> None:
    """Create a minimal temporary database for rejection testing."""

    connection = sqlite3.connect(db_path)

    try:
        cursor = connection.cursor()

        cursor.executescript(
            """
            CREATE TABLE stations (
                station_code TEXT PRIMARY KEY,
                station_name TEXT NOT NULL,
                station_category TEXT,
                station_daily_passengers INTEGER
            );

            CREATE TABLE platforms (
                resource_id TEXT PRIMARY KEY,
                station_code TEXT NOT NULL,
                platform_number INTEGER NOT NULL,
                platform_type TEXT NOT NULL
            );

            CREATE TABLE timetable (
                timetable_record_id INTEGER PRIMARY KEY,
                train_number TEXT NOT NULL,
                station_code TEXT NOT NULL,
                day INTEGER NOT NULL,
                stop_number INTEGER NOT NULL,
                arrival TEXT,
                departure TEXT,
                resource_id TEXT,
                platform_number INTEGER,
                platform_type TEXT
            );

            CREATE TABLE resource_allocations (
                allocation_id TEXT PRIMARY KEY,
                timetable_record_id INTEGER NOT NULL,
                station_code TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                day INTEGER NOT NULL,
                allocation_start TEXT NOT NULL,
                allocation_end TEXT NOT NULL,
                buffer_minutes INTEGER NOT NULL,
                release_time TEXT
            );

            CREATE TABLE trains (
                train_number TEXT PRIMARY KEY,
                train_name TEXT,
                train_type TEXT,
                priority INTEGER
            );
            """
        )

        # ---------------------------------------------------------
        # Station
        # ---------------------------------------------------------
        cursor.execute(
            """
            INSERT INTO stations
            VALUES (?, ?, ?, ?)
            """,
            (
                "TEST",
                "Synthetic Test Station",
                "A",
                10000,
            ),
        )

        # ---------------------------------------------------------
        # Platforms
        # ---------------------------------------------------------
        cursor.executemany(
            """
            INSERT INTO platforms
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    "TEST-P1",
                    "TEST",
                    1,
                    "MAINLINE",
                ),
                (
                    "TEST-P2",
                    "TEST",
                    2,
                    "MAINLINE",
                ),
            ],
        )

        # ---------------------------------------------------------
        # Train
        # ---------------------------------------------------------
        cursor.execute(
            """
            INSERT INTO trains
            VALUES (?, ?, ?, ?)
            """,
            (
                "T001",
                "Synthetic Test Train",
                "EXPRESS",
                1,
            ),
        )

        # ---------------------------------------------------------
        # Timetable
        # ---------------------------------------------------------
        cursor.execute(
            """
            INSERT INTO timetable
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1001,
                "T001",
                "TEST",
                1,
                1,
                "10:00:00",
                "10:10:00",
                "TEST-P1",
                1,
                "MAINLINE",
            ),
        )

        # ---------------------------------------------------------
        # Original resource allocation
        # ---------------------------------------------------------
        cursor.execute(
            """
            INSERT INTO resource_allocations
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "RA-1001",
                1001,
                "TEST",
                "TEST-P1",
                1,
                "10:00:00",
                "10:10:00",
                5,
                "10:15:00",
            ),
        )

        connection.commit()

    finally:
        connection.close()


def create_synthetic_passenger_csv(
    csv_path: Path,
) -> None:
    """Create temporary passenger data for the synthetic station."""

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "station_code",
                "category",
                "daily_passengers",
            ],
        )

        writer.writeheader()

        writer.writerow(
            {
                "station_code": "TEST",
                "category": "A",
                "daily_passengers": 10000,
            }
        )


def create_initial_solution() -> ALNSSolution:
    """Create the initial timetable solution."""

    record = TimetableRecord(
        timetable_record_id=1001,
        train_number="T001",
        station_code="TEST",
        day=1,
        stop_number=1,
        arrival="10:00:00",
        departure="10:10:00",
        resource_id="TEST-P1",
        platform_number=1,
        platform_type="MAINLINE",
    )

    return ALNSSolution(
        records={
            1001: record,
        }
    )


def create_disruption() -> Disruption:
    """Create the synthetic platform closure."""

    return Disruption(
        disruption_type="PLATFORM_CLOSURE",
        station_code="TEST",
        resource_id="TEST-P1",
        start_time="10:00:00",
        end_time="10:20:00",
        day=1,
    )


def main() -> None:
    """Run the genuine feasible/infeasible candidate test."""

    with tempfile.TemporaryDirectory(
        prefix="alns_rejection_"
    ) as temp_directory:

        temp_dir = Path(temp_directory)

        db_path = temp_dir / "test_railway.db"

        passenger_csv_path = (
            temp_dir / "test_passenger_data.csv"
        )

        # ---------------------------------------------------------
        # Create isolated synthetic inputs.
        # ---------------------------------------------------------
        create_synthetic_database(
            db_path
        )

        create_synthetic_passenger_csv(
            passenger_csv_path
        )

        initial_solution = (
            create_initial_solution()
        )

        disruption = (
            create_disruption()
        )

        # ---------------------------------------------------------
        # Real CandidateBuilder.
        # ---------------------------------------------------------
        candidate_builder = (
            CandidateBuilder()
        )

        # ---------------------------------------------------------
        # Real CandidateEvaluator.
        #
        # Uses:
        #   - temporary SQLite database
        #   - temporary passenger CSV
        #   - real ML model
        #   - real FeasibilityChecker
        # ---------------------------------------------------------
        evaluator = CandidateEvaluator(
            db_path=db_path,
            passenger_data_path=(
                passenger_csv_path
            ),
            disruption=disruption,
        )

        # =========================================================
        # CANDIDATE A
        # =========================================================
        #
        # Move T001 from closed P1 to valid P2.
        #
        # Expected:
        #   Feasible = True
        #   Objective = finite
        #
        # =========================================================

        feasible_modification = (
            TimetableModification(
                timetable_record_id=1001,
                new_resource_id="TEST-P2",
                new_platform_number=2,
                new_platform_type="MAINLINE",
                reason=(
                    "Synthetic feasible "
                    "reassignment"
                ),
            )
        )

        feasible_candidate = (
            candidate_builder.apply_modification(
                initial_solution,
                feasible_modification,
            )
        )

        feasible_candidate = (
            evaluator.evaluate(
                feasible_candidate,
                affected_train_count=1,
            )
        )

        # =========================================================
        # CANDIDATE B
        # =========================================================
        #
        # Keep T001 on closed P1 during the disruption.
        #
        # We change the departure time so the record is considered
        # modified and therefore receives complete feasibility
        # validation.
        #
        # Expected:
        #   Feasible = False
        #   Objective = inf
        #
        # =========================================================

        infeasible_modification = (
            TimetableModification(
                timetable_record_id=1001,
                new_departure="10:11:00",
                new_resource_id="TEST-P1",
                new_platform_number=1,
                new_platform_type="MAINLINE",
                reason=(
                    "Synthetic infeasible "
                    "reassignment"
                ),
            )
        )

        infeasible_candidate = (
            candidate_builder.apply_modification(
                initial_solution,
                infeasible_modification,
            )
        )

        infeasible_candidate = (
            evaluator.evaluate(
                infeasible_candidate,
                affected_train_count=1,
            )
        )

        # =========================================================
        # DISPLAY RESULTS
        # =========================================================

        print()
        print(
            "SYNTHETIC ALNS REJECTION TEST"
        )
        print(
            "============================="
        )
        print()

        print("Disruption:")
        print("  Station   : TEST")
        print("  Resource  : TEST-P1")
        print(
            "  Closure   : "
            "10:00:00 -> 10:20:00"
        )
        print()

        # ---------------------------------------------------------
        # Candidate A
        # ---------------------------------------------------------
        print(
            "Candidate A - Feasible"
        )
        print(
            "----------------------"
        )

        print(
            "  Assignment : "
            "TEST-P1 -> TEST-P2"
        )

        print(
            "  Feasible   : "
            f"{feasible_candidate.is_feasible}"
        )

        print(
            "  Objective  : "
            f"{feasible_candidate.objective_value}"
        )

        print(
            "  Delay      : "
            f"{feasible_candidate.total_delay_minutes}"
        )

        print(
            "  Passenger  : "
            f"{feasible_candidate.passenger_impact_minutes}"
        )

        print()

        # ---------------------------------------------------------
        # Candidate B
        # ---------------------------------------------------------
        print(
            "Candidate B - Infeasible"
        )
        print(
            "------------------------"
        )

        print(
            "  Assignment : "
            "TEST-P1 -> TEST-P1 "
            "(during closure)"
        )

        print(
            "  Feasible   : "
            f"{infeasible_candidate.is_feasible}"
        )

        print(
            "  Objective  : "
            f"{infeasible_candidate.objective_value}"
        )

        print(
            "  Delay      : "
            f"{infeasible_candidate.total_delay_minutes}"
        )

        print(
            "  Passenger  : "
            f"{infeasible_candidate.passenger_impact_minutes}"
        )

        print()

        # =========================================================
        # ASSERTIONS
        # =========================================================

        if not feasible_candidate.is_feasible:
            raise AssertionError(
                "Candidate A should be feasible."
            )

        if (
            feasible_candidate.objective_value
            == float("inf")
        ):
            raise AssertionError(
                "Candidate A should have "
                "a finite objective."
            )

        if infeasible_candidate.is_feasible:
            raise AssertionError(
                "Candidate B should be "
                "infeasible."
            )

        if (
            infeasible_candidate.objective_value
            != float("inf")
        ):
            raise AssertionError(
                "Infeasible Candidate B must "
                "receive objective = inf."
            )

        # =========================================================
        # FINAL RESULT
        # =========================================================

        print("RESULT")
        print("------")

        print(
            "PASS - The real evaluator correctly "
            "distinguished feasible and "
            "infeasible candidates."
        )

        print(
            "PASS - The infeasible candidate "
            "received objective = inf."
        )

        print(
            "PASS - Production database and "
            "passenger dataset were not modified."
        )


if __name__ == "__main__":
    main()
