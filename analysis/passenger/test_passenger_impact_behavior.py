
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import sys


# ============================================================
# PROJECT ROOT / IMPORT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# PROJECT IMPORTS
# ============================================================

from src.optimization.alns_data_loader import load_initial_solution
from src.optimization.alns_disruption import Disruption
from src.optimization.alns_candidate import CandidateBuilder
from src.optimization.alns_move import TimetableModification
from src.optimization.alns_evaluation import CandidateEvaluator


# ============================================================
# PATHS
# ============================================================

DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "database"
    / "railway_recovery.db"
)


# ============================================================
# FIND TIMETABLE RECORD
# ============================================================

def find_mas_record(
    target_hour,
    target_minute,
):
    """
    Find a MAS timetable record close to the requested time.

    The record must:
    - belong to MAS
    - be on day 1
    - have a departure time
    - have a platform/resource
    """

    target_minutes = (
        target_hour * 60
        + target_minute
    )

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            timetable_record_id,
            train_number,
            station_code,
            day,
            departure,
            resource_id,
            platform_number,
            platform_type
        FROM timetable
        WHERE station_code = 'MAS'
          AND day = 1
          AND departure IS NOT NULL
          AND resource_id IS NOT NULL
          AND platform_number IS NOT NULL
        """
    )

    rows = cursor.fetchall()

    connection.close()

    if not rows:
        raise RuntimeError(
            "No suitable MAS timetable records were found."
        )

    best_record = None
    best_difference = None

    for row in rows:

        (
            timetable_record_id,
            train_number,
            station_code,
            day,
            departure,
            resource_id,
            platform_number,
            platform_type,
        ) = row

        try:
            time_object = datetime.strptime(
                departure,
                "%H:%M:%S"
            )

        except ValueError:
            continue

        record_minutes = (
            time_object.hour * 60
            + time_object.minute
        )

        difference = abs(
            record_minutes - target_minutes
        )

        # Prefer records that are not on P4 because
        # P4 will be the disrupted resource.
        if resource_id == "MAS-P4":
            difference += 10000

        if (
            best_difference is None
            or difference < best_difference
        ):
            best_difference = difference
            best_record = {
                "timetable_record_id": timetable_record_id,
                "train_number": train_number,
                "station_code": station_code,
                "day": day,
                "departure": departure,
                "resource_id": resource_id,
                "platform_number": platform_number,
                "platform_type": platform_type,
            }

    if best_record is None:
        raise RuntimeError(
            f"No suitable MAS record found near "
            f"{target_hour:02d}:{target_minute:02d}."
        )

    return best_record


# ============================================================
# BUILD CANDIDATE
# ============================================================

def build_candidate(
    initial_solution,
    record,
    delay_minutes,
    alternative_platform,
):
    """
    Move a timetable record to another platform and
    add a specified delay.
    """

    builder = CandidateBuilder()

    original = initial_solution.get_record(
        record["timetable_record_id"]
    )

    if original.departure is None:
        raise ValueError(
            f"Record {record['timetable_record_id']} "
            "does not have a departure time."
        )

    original_time = datetime.strptime(
        original.departure,
        "%H:%M:%S"
    )

    new_time = original_time + timedelta(
        minutes=delay_minutes
    )

    new_departure = new_time.strftime(
        "%H:%M:%S"
    )

    modification = TimetableModification(
        timetable_record_id=(
            record["timetable_record_id"]
        ),
        new_departure=new_departure,
        new_resource_id=alternative_platform[
            "resource_id"
        ],
        new_platform_number=alternative_platform[
            "platform_number"
        ],
        new_platform_type=alternative_platform[
            "platform_type"
        ],
        reason=(
            f"PEAK_BEHAVIOR_TEST_{delay_minutes}MIN"
        ),
    )

    candidate = builder.apply_modification(
        initial_solution,
        modification,
    )

    return (
        candidate,
        original.departure,
        new_departure,
    )


# ============================================================
# FIND ALTERNATIVE PLATFORM
# ============================================================

def find_alternative_platform(
    station_code,
    original_resource_id,
):
    """
    Find a platform at the same station that is different
    from the original resource.
    """

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            resource_id,
            platform_number,
            platform_type
        FROM platforms
        WHERE station_code = ?
          AND resource_id != ?
        ORDER BY platform_number
        """,
        (
            station_code,
            original_resource_id,
        ),
    )

    rows = cursor.fetchall()

    connection.close()

    if not rows:
        raise RuntimeError(
            f"No alternative platform found at "
            f"{station_code}."
        )

    for row in rows:

        resource_id, platform_number, platform_type = row

        # Prefer MAINLINE for this test.
        if platform_type == "MAINLINE":
            return {
                "resource_id": resource_id,
                "platform_number": platform_number,
                "platform_type": platform_type,
            }

    # Fall back to the first available platform.
    resource_id, platform_number, platform_type = rows[0]

    return {
        "resource_id": resource_id,
        "platform_number": platform_number,
        "platform_type": platform_type,
    }


# ============================================================
# EVALUATE ONE SCENARIO
# ============================================================

def evaluate_scenario(
    initial_solution,
    record,
    disruption,
    delay_minutes,
    alternative_platform,
):
    """
    Build and evaluate one candidate.
    """

    evaluator = CandidateEvaluator(
        db_path=DB_PATH,
        disruption=disruption,
    )

    (
        candidate,
        original_departure,
        new_departure,
    ) = build_candidate(
        initial_solution=initial_solution,
        record=record,
        delay_minutes=delay_minutes,
        alternative_platform=alternative_platform,
    )

    evaluator.evaluate(candidate)

    evaluation = evaluator.get_evaluation_summary(
        candidate
    )

    return {
        "record_id": record[
            "timetable_record_id"
        ],
        "train_number": record[
            "train_number"
        ],
        "original_resource": record[
            "resource_id"
        ],
        "alternative_resource": alternative_platform[
            "resource_id"
        ],
        "original_departure": original_departure,
        "candidate_departure": new_departure,
        "total_delay": evaluation[
            "total_delay_minutes"
        ],
        "passenger_impact": evaluation[
            "passenger_impact_minutes"
        ],
        "objective": evaluation[
            "objective_value"
        ],
        "feasible": evaluation[
            "is_feasible"
        ],
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("PASSENGER IMPACT — PEAK VS NON-PEAK TEST")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. Load timetable
    # --------------------------------------------------------

    print("\nLoading initial timetable...")

    initial_solution = load_initial_solution(
        DB_PATH
    )

    print(
        f"Loaded records: "
        f"{initial_solution.record_count()}"
    )

    # --------------------------------------------------------
    # 2. Find morning peak record
    # --------------------------------------------------------

    print(
        "\nSearching for MAS morning-peak record..."
    )

    peak_record = find_mas_record(
        target_hour=8,
        target_minute=30,
    )

    print(
        f"Peak record: "
        f"{peak_record['timetable_record_id']}"
    )

    print(
        f"Train: "
        f"{peak_record['train_number']}"
    )

    print(
        f"Departure: "
        f"{peak_record['departure']}"
    )

    print(
        f"Platform: "
        f"{peak_record['resource_id']}"
    )

    # --------------------------------------------------------
    # 3. Find non-peak record
    # --------------------------------------------------------

    print(
        "\nSearching for MAS non-peak record..."
    )

    non_peak_record = find_mas_record(
        target_hour=13,
        target_minute=0,
    )

    print(
        f"Non-peak record: "
        f"{non_peak_record['timetable_record_id']}"
    )

    print(
        f"Train: "
        f"{non_peak_record['train_number']}"
    )

    print(
        f"Departure: "
        f"{non_peak_record['departure']}"
    )

    print(
        f"Platform: "
        f"{non_peak_record['resource_id']}"
    )

    # --------------------------------------------------------
    # 4. Find alternative platforms
    # --------------------------------------------------------

    peak_platform = find_alternative_platform(
        "MAS",
        peak_record["resource_id"],
    )

    non_peak_platform = find_alternative_platform(
        "MAS",
        non_peak_record["resource_id"],
    )

    print(
        "\nPeak alternative platform: "
        f"{peak_platform['resource_id']}"
    )

    print(
        "Non-peak alternative platform: "
        f"{non_peak_platform['resource_id']}"
    )

    # --------------------------------------------------------
    # 5. Create disruptions
    # --------------------------------------------------------
    #
    # The disruption resource is P4.
    # We use the same 60-minute disruption duration.
    #

    peak_disruption = Disruption(
        disruption_type="PLATFORM_CLOSURE",
        station_code="MAS",
        resource_id="MAS-P4",
        start_time="08:00:00",
        end_time="09:00:00",
        day=1,
    )

    non_peak_disruption = Disruption(
        disruption_type="PLATFORM_CLOSURE",
        station_code="MAS",
        resource_id="MAS-P4",
        start_time="13:00:00",
        end_time="14:00:00",
        day=1,
    )

    # --------------------------------------------------------
    # 6. Evaluate peak scenario
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("TESTING MORNING PEAK")
    print("=" * 70)

    peak_result = evaluate_scenario(
        initial_solution=initial_solution,
        record=peak_record,
        disruption=peak_disruption,
        delay_minutes=15,
        alternative_platform=peak_platform,
    )

    # --------------------------------------------------------
    # 7. Evaluate non-peak scenario
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("TESTING NON-PEAK")
    print("=" * 70)

    non_peak_result = evaluate_scenario(
        initial_solution=initial_solution,
        record=non_peak_record,
        disruption=non_peak_disruption,
        delay_minutes=15,
        alternative_platform=non_peak_platform,
    )

    # --------------------------------------------------------
    # 8. Display results
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("COMPARISON")
    print("=" * 70)

    print("\nMORNING PEAK")
    print("-" * 70)

    print(
        f"Record:             "
        f"{peak_result['record_id']}"
    )

    print(
        f"Train:              "
        f"{peak_result['train_number']}"
    )

    print(
        f"Original departure: "
        f"{peak_result['original_departure']}"
    )

    print(
        f"Candidate departure:"
        f" {peak_result['candidate_departure']}"
    )

    print(
        f"Delay:              "
        f"{peak_result['total_delay']:.2f} minutes"
    )

    print(
        f"Passenger impact:   "
        f"{peak_result['passenger_impact']:.2f}"
    )

    print(
        f"Objective:          "
        f"{peak_result['objective']:.6f}"
    )

    print(
        f"Feasible:           "
        f"{peak_result['feasible']}"
    )

    print("\nNON-PEAK")
    print("-" * 70)

    print(
        f"Record:             "
        f"{non_peak_result['record_id']}"
    )

    print(
        f"Train:              "
        f"{non_peak_result['train_number']}"
    )

    print(
        f"Original departure: "
        f"{non_peak_result['original_departure']}"
    )

    print(
        f"Candidate departure:"
        f" {non_peak_result['candidate_departure']}"
    )

    print(
        f"Delay:              "
        f"{non_peak_result['total_delay']:.2f} minutes"
    )

    print(
        f"Passenger impact:   "
        f"{non_peak_result['passenger_impact']:.2f}"
    )

    print(
        f"Objective:          "
        f"{non_peak_result['objective']:.6f}"
    )

    print(
        f"Feasible:           "
        f"{non_peak_result['feasible']}"
    )

    # --------------------------------------------------------
    # 9. Behavioral interpretation
    # --------------------------------------------------------

    peak_impact = peak_result[
        "passenger_impact"
    ]

    non_peak_impact = non_peak_result[
        "passenger_impact"
    ]

    print("\n")
    print("=" * 70)
    print("BEHAVIORAL CHECK")
    print("=" * 70)

    print(
        f"\nMorning peak impact: "
        f"{peak_impact:.2f}"
    )

    print(
        f"Non-peak impact:     "
        f"{non_peak_impact:.2f}"
    )

    print()

    if peak_impact > non_peak_impact:

        print(
            "PASS: Morning peak produced "
            "higher passenger impact."
        )

    elif peak_impact < non_peak_impact:

        print(
            "NOTICE: Non-peak produced "
            "higher passenger impact."
        )

    else:

        print(
            "NOTICE: Both scenarios produced "
            "the same passenger impact."
        )

    # --------------------------------------------------------
    # 10. Feasibility
    # --------------------------------------------------------

    print()

    if (
        peak_result["feasible"]
        and non_peak_result["feasible"]
    ):

        print(
            "PASS: Both candidates are feasible."
        )

    else:

        print(
            "NOTICE: One or both candidates "
            "are infeasible."
        )

    print("\n")
    print("=" * 70)
    print("TEST COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()

