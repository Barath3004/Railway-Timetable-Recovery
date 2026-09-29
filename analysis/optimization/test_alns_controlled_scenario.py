import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.optimization.alns_disruption import Disruption
from src.optimization.alns_optimizer import ALNSOptimizer

DB_PATH = PROJECT_ROOT / "data" / "database" / "railway_recovery.db"


def main():
    print("=" * 80)
    print("CONTROLLED ALNS END-TO-END DIAGNOSTIC")
    print("=" * 80)

    print(f"\nDatabase: {DB_PATH}")
    print(f"Database exists: {DB_PATH.exists()}")

    # ---------------------------------------------------------
    # CONTROLLED DISRUPTION
    # ---------------------------------------------------------
    disruption = Disruption(
        disruption_type="PLATFORM_CLOSURE",
        station_code="MS",
        resource_id="MS-P9",
        start_time="05:00:00",
        end_time="05:20:00",
        day=1,
    )

    print("\n" + "-" * 80)
    print("1. DISRUPTION")
    print("-" * 80)

    print(f"Type      : {disruption.disruption_type}")
    print(f"Station   : {disruption.station_code}")
    print(f"Resource  : {disruption.resource_id}")
    print(f"Start     : {disruption.start_time}")
    print(f"End       : {disruption.end_time}")
    print(f"Day       : {disruption.day}")

    # ---------------------------------------------------------
    # RUN EXISTING OPTIMIZER
    # ---------------------------------------------------------
    print("\n" + "-" * 80)
    print("2. RUNNING EXISTING ALNS OPTIMIZER")
    print("-" * 80)

    optimizer = ALNSOptimizer(DB_PATH)

    result = optimizer.optimize(
        disruption,
        iterations=10,
        max_candidates=100,
    )

    # ---------------------------------------------------------
    # BASIC RESULT
    # ---------------------------------------------------------
    print("\n" + "-" * 80)
    print("3. OPTIMIZATION RESULT")
    print("-" * 80)

    print(f"Iterations executed       : {result.iterations}")
    print(f"Candidates generated      : {result.candidates_generated_count}")
    print(f"Feasible candidates       : {result.feasible_candidates_count}")
    print(f"Repairs generated         : {len(result.repairs_generated)}")
    print(f"Execution time            : {result.execution_time_seconds:.3f} sec")

    # ---------------------------------------------------------
    # AFFECTED RECORDS
    # ---------------------------------------------------------
    print("\n" + "-" * 80)
    print("4. AFFECTED RECORDS")
    print("-" * 80)

    print(f"Count: {len(result.affected_records)}")

    for record in result.affected_records:
        print(
            f"Record {record.timetable_record_id} | "
            f"Train {record.train_number} | "
            f"Station {record.station_code} | "
            f"Platform {record.platform_number} | "
            f"Arrival {record.arrival} | "
            f"Departure {record.departure}"
        )

    # ---------------------------------------------------------
    # BEST SOLUTION
    # ---------------------------------------------------------
    print("\n" + "-" * 80)
    print("5. BEST SOLUTION")
    print("-" * 80)

    if result.best_solution is None:
        print("NO FEASIBLE SOLUTION FOUND.")
    else:
        print(f"Objective          : {result.best_objective:.6f}")
        print(f"Total delay        : {result.best_total_delay}")
        print(f"Passenger impact   : {result.best_passenger_impact}")
        print(f"Feasible           : {result.best_solution.is_feasible}")

    # ---------------------------------------------------------
    # TOP SOLUTIONS
    # ---------------------------------------------------------
    print("\n" + "-" * 80)
    print("6. TOP SOLUTIONS")
    print("-" * 80)

    if not result.top_solutions:
        print("No top solutions returned.")
    else:
        for index, solution in enumerate(result.top_solutions, start=1):
            print(f"\n--- TOP {index} ---")
            print(f"Objective        : {solution.objective_value:.6f}")
            print(f"Total delay      : {solution.total_delay_minutes}")
            print(f"Passenger impact : {solution.passenger_impact_minutes}")
            print(f"Feasible         : {solution.is_feasible}")

            for record in result.affected_records:
                candidate_record = solution.get_record(
                    record.timetable_record_id
                )

                print(
                    f"Record {record.timetable_record_id} | "
                    f"Train {record.train_number} | "
                    f"Original platform={record.platform_number} | "
                    f"New platform={candidate_record.platform_number} | "
                    f"Original resource={record.resource_id} | "
                    f"New resource={candidate_record.resource_id} | "
                    f"Arrival={candidate_record.arrival} | "
                    f"Departure={candidate_record.departure}"
                )

    # ---------------------------------------------------------
    # DIAGNOSTIC CONCLUSION
    # ---------------------------------------------------------
    print("\n" + "=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)

    if result.iterations == 1:
        print("WARNING: Requested 10 iterations, but only 1 iteration executed.")
        print("This confirms the current optimizer is not performing")
        print("multiple ALNS search iterations.")
    else:
        print("Multiple iterations were executed.")

    if result.candidates_generated_count > 0:
        print("Candidate generation: WORKING")
    else:
        print("Candidate generation: FAILED")

    if result.feasible_candidates_count > 0:
        print("Feasibility filtering: WORKING")
    else:
        print("Feasibility filtering: NO FEASIBLE CANDIDATES")

    if len(result.top_solutions) > 0:
        print("Top-solution selection: WORKING")
    else:
        print("Top-solution selection: FAILED")

    print("=" * 80)


if __name__ == "__main__":
    main()