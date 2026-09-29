
import sys
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.optimization.alns_data_loader import load_initial_solution
from src.optimization.alns_disruption import Disruption, DisruptionFilter
from src.optimization.alns_move import TimetableModification
from src.optimization.alns_candidate import CandidateBuilder
from src.optimization.alns_evaluation import CandidateEvaluator
from src.optimization.alns_feasibility import FeasibilityChecker

DB = ROOT / "data" / "database" / "railway_recovery.db"

RECORD_IDS = [269889, 351622, 322226]


def add_minutes(value, minutes):
    time = datetime.strptime(value, "%H:%M:%S")
    return (time + timedelta(minutes=minutes)).strftime("%H:%M:%S")


def modify(solution, record_id, platform, delay=0,
           arrival_override=None):
    original = solution.get_record(record_id)

    arrival = (
        arrival_override
        if arrival_override is not None
        else add_minutes(original.original_arrival, delay)
    )
    departure = add_minutes(original.original_departure, delay)

    modification = TimetableModification(
        timetable_record_id=record_id,
        new_arrival=arrival,
        new_departure=departure,
        new_resource_id=f"MS-P{platform}",
        new_platform_number=platform,
        new_platform_type="MAINLINE",
        reason="Controlled ALNS stress test"
    )

    return CandidateBuilder.apply_modification(
        solution, modification
    )


def show_result(name, solution, evaluator, checker, affected_count):
    feasible, violations = checker.check_solution(solution)

    evaluated = evaluator.evaluate(
        solution,
        affected_train_count=affected_count
    )

    print("\n" + "=" * 75)
    print(name)
    print("=" * 75)

    for record_id in RECORD_IDS:
        record = evaluated.get_record(record_id)
        print(
            f"Record {record_id} | "
            f"{record.resource_id} | "
            f"{record.arrival} - {record.departure}"
        )

    print(f"Feasible         : {evaluated.is_feasible}")
    print(f"Total delay      : {evaluated.total_delay_minutes}")
    print(f"Passenger impact : {evaluated.passenger_impact_minutes}")
    print(f"Objective        : {evaluated.objective_value}")

    if not feasible:
        print("VIOLATIONS:")
        for record_id, problems in violations.items():
            print(f"  Record {record_id}: {problems}")

    return evaluated


def main():
    disruption = Disruption(
        disruption_type="PLATFORM_CLOSURE",
        station_code="MS",
        resource_id="MS-P9",
        start_time="05:00:00",
        end_time="05:35:00",
        day=1
    )

    initial = load_initial_solution(DB)

    affected = DisruptionFilter(DB).find_affected_records(
        disruption, initial
    )

    print("=" * 75)
    print("CONTROLLED ALNS STRESS TEST")
    print("=" * 75)

    print("\nAffected records:")
    for record in affected:
        print(
            record.timetable_record_id,
            record.train_number,
            record.resource_id,
            record.arrival,
            record.departure
        )

    found = {r.timetable_record_id for r in affected}
    missing = set(RECORD_IDS) - found

    if missing:
        print(f"\nSTOP: Expected affected records missing: {missing}")
        return

    evaluator = CandidateEvaluator(
        db_path=DB,
        disruption=disruption
    )
    checker = FeasibilityChecker(DB, disruption=disruption)
    affected_count = len({r.train_number for r in affected})

    # Candidate A: Three different platforms, no delay.
    a = initial.copy()
    for record_id, platform in zip(RECORD_IDS, [1, 2, 3]):
        a = modify(a, record_id, platform)

    show_result(
        "A: Separate platforms, zero delay",
        a, evaluator, checker, affected_count
    )

    # Candidate B: Same assignment, second train delayed 5 min.
    b = initial.copy()
    for record_id, platform in zip(RECORD_IDS, [1, 2, 3]):
        b = modify(
            b, record_id, platform,
            delay=5 if record_id == RECORD_IDS[1] else 0
        )

    show_result(
        "B: Separate platforms, 5-minute delay",
        b, evaluator, checker, affected_count
    )

    # Candidate C: Same assignment, second train delayed 15 min.
    c = initial.copy()
    for record_id, platform in zip(RECORD_IDS, [1, 2, 3]):
        c = modify(
            c, record_id, platform,
            delay=15 if record_id == RECORD_IDS[1] else 0
        )

    show_result(
        "C: Separate platforms, 15-minute delay",
        c, evaluator, checker, affected_count
    )

    # Candidate D: Deliberate overlap on P1.
    # The second train arrives while the first still occupies P1.
    d = initial.copy()
    d = modify(d, RECORD_IDS[0], 1)
    d = modify(
        d, RECORD_IDS[1], 1,
        arrival_override="04:49:00"
    )
    d = modify(d, RECORD_IDS[2], 3)

    show_result(
        "D: Deliberate overlapping platform assignment",
        d, evaluator, checker, affected_count
    )

    # Candidate E: Assign the second train to the closed platform.
    e = initial.copy()
    e = modify(e, RECORD_IDS[0], 1)
    e = modify(e, RECORD_IDS[1], 9)
    e = modify(e, RECORD_IDS[2], 3)

    show_result(
        "E: Assignment to closed platform P9",
        e, evaluator, checker, affected_count
    )

    print("\n" + "=" * 75)
    print("STRESS TEST FINISHED")
    print("=" * 75)


if __name__ == "__main__":
    main()