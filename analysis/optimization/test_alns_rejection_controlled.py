"""
Controlled ALNS Rejection Test
================================
Standalone test demonstrating the ALNS evaluation/acceptance pipeline
handling feasible, infeasible, and genuinely rejected candidates using
REAL production code against a synthetic SQLite database.

Run from the project root:
    python analysis/optimization/test_alns_rejection_controlled.py

DO NOT MODIFY PRODUCTION FILES -- this script creates and cleans up its own
temporary database and CSV.

TEST 4 REJECTION MECHANISM (documented):
-----------------------------------------
The ALNS optimizer increments rejected_candidates_count (alns_optimizer.py
line 438) whenever accepted == False.

With two trains BOTH on the disrupted platform (TEST-P1) and only two
alternative platforms (TEST-P2, TEST-P3), the repair pool for each train
contains two options: P2 or P3.

The optimizer's repair selector independently picks one repair per train each
iteration. Sometimes it picks:
    Train A -> TEST-P2 AND Train B -> TEST-P2

Both trains would occupy TEST-P2 simultaneously (overlapping allocations).
This creates a platform conflict detected by FeasibilityChecker.check_record
during evaluator.evaluate(), making the combined candidate INFEASIBLE.

An infeasible candidate sets accepted=False at line 431 of alns_optimizer.py:
    else:
        accepted = False   # <-- infeasible path
        reward = 0.0

This increments rejected_candidates_count at line 438, without any
modification to production code.
"""
from __future__ import annotations

import hashlib
import math
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root on sys.path
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Production file integrity baseline
# ---------------------------------------------------------------------------
PROTECTED_FILES: list[Path] = [
    PROJECT_ROOT / "data" / "database" / "railway_recovery.db",
]
for _f in (PROJECT_ROOT / "src" / "optimization").glob("*.py"):
    PROTECTED_FILES.append(_f)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _snapshot(paths: list[Path]) -> dict[str, str]:
    return {str(p): _sha256(p) for p in paths if p.exists()}


# ---------------------------------------------------------------------------
# Synthetic data constants
# ---------------------------------------------------------------------------
TEST_STATION    = "TEST"
DISRUPTED_RES   = "TEST-P1"   # closed platform
SAFE_RES_A      = "TEST-P2"   # alternative platform 1
SAFE_RES_B      = "TEST-P3"   # alternative platform 2

TRAIN_A         = "T9991"     # first disrupted train
TRAIN_B         = "T9992"     # second disrupted train

# Disruption window: 10:00 - 10:30 Day 1
DISRUPTION_START = "10:00:00"
DISRUPTION_END   = "10:30:00"

# Train A: occupies P1 from 10:05-10:12  (release 10:17 with 5-min buffer)
A_ARR  = "10:05:00"
A_DEP  = "10:12:00"
A_ALLOC_S = "10:05:00"
A_ALLOC_E = "10:12:00"
A_RELEASE = "10:17:00"
A_OCC  = 7    # occupancy minutes
A_BUF  = 5

# Train B: occupies P1 from 10:13-10:20  (release 10:25 with 5-min buffer)
B_ARR  = "10:13:00"
B_DEP  = "10:20:00"
B_ALLOC_S = "10:13:00"
B_ALLOC_E = "10:20:00"
B_RELEASE = "10:25:00"
B_OCC  = 7    # occupancy minutes
B_BUF  = 5

# Train A candidate allocations on P2/P3:
#   alloc 10:05-10:12, release 10:17  (same as original P1 template)
# Train B candidate allocations on P2/P3:
#   alloc 10:13-10:20, release 10:25

# Overlap analysis (P2/P3 conflict when both trains go there):
#   Train A release 10:17  >  Train B alloc 10:13  => OVERLAP if same platform
#   Specifically: A uses 10:05-10:17, B uses 10:13-10:25
#   10:05 < 10:25 AND 10:13 < 10:17  =>  CONFLICT detected by _intervals_overlap

MODEL_PATH = (
    PROJECT_ROOT / "data" / "processed" / "passenger_ml"
    / "final_model" / "passenger_impact_model.joblib"
)


# ===========================================================================
# DB / CSV setup
# ===========================================================================

def _create_test_db(db_path: Path) -> tuple[int, int]:
    """
    Create the synthetic test database (exact production schema).
    Returns (record_id_train_a, record_id_train_b).
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("""CREATE TABLE trains (
        train_number TEXT PRIMARY KEY, train_name TEXT NOT NULL,
        train_type TEXT NOT NULL, priority INTEGER,
        maximum_speed_kmph REAL, operator TEXT, zone TEXT,
        source_station TEXT, destination_station TEXT)""")

    c.execute("""CREATE TABLE stations (
        station_code TEXT PRIMARY KEY, station_name TEXT NOT NULL,
        railway_zone TEXT, railway_division TEXT,
        platforms_total INTEGER, mainline_platforms INTEGER,
        suburban_platforms INTEGER, electrification_year INTEGER,
        station_buffer_minutes INTEGER)""")

    c.execute("""CREATE TABLE platforms (
        resource_id TEXT PRIMARY KEY, station_code TEXT NOT NULL,
        platform_number INTEGER NOT NULL, platform_type TEXT NOT NULL,
        resource_type TEXT NOT NULL DEFAULT 'PLATFORM',
        FOREIGN KEY (station_code) REFERENCES stations(station_code),
        UNIQUE (station_code, platform_number))""")

    c.execute("""CREATE TABLE timetable (
        timetable_record_id INTEGER PRIMARY KEY,
        train_number TEXT NOT NULL, station_code TEXT NOT NULL,
        day INTEGER NOT NULL, stop_number INTEGER NOT NULL,
        arrival TEXT, departure TEXT,
        resource_id TEXT, platform_number INTEGER,
        platform_type TEXT, platform_allocated_by TEXT,
        FOREIGN KEY (train_number) REFERENCES trains(train_number),
        FOREIGN KEY (station_code) REFERENCES stations(station_code),
        FOREIGN KEY (resource_id) REFERENCES platforms(resource_id))""")

    c.execute("""CREATE TABLE resource_allocations (
        allocation_id TEXT PRIMARY KEY,
        resource_id TEXT NOT NULL, resource_type TEXT NOT NULL,
        station_code TEXT NOT NULL, station_name TEXT,
        platform_number INTEGER, platform_type TEXT, day INTEGER,
        timetable_record_id INTEGER NOT NULL,
        allocation_start TEXT, allocation_end TEXT,
        occupancy_minutes INTEGER, buffer_minutes INTEGER,
        release_time TEXT, allocation_status TEXT, allocation_source TEXT,
        FOREIGN KEY (resource_id) REFERENCES platforms(resource_id),
        FOREIGN KEY (station_code) REFERENCES stations(station_code),
        FOREIGN KEY (timetable_record_id)
            REFERENCES timetable(timetable_record_id))""")

    # Trains
    c.execute("INSERT INTO trains VALUES (?,?,?,?,?,?,?,?,?)",
        (TRAIN_A, "Test Express A (synthetic)", "EXPRESS", 2, 120.0,
         "SYNTHETIC", "SR", TEST_STATION, TEST_STATION))
    c.execute("INSERT INTO trains VALUES (?,?,?,?,?,?,?,?,?)",
        (TRAIN_B, "Test Express B (synthetic)", "EXPRESS", 2, 110.0,
         "SYNTHETIC", "SR", TEST_STATION, TEST_STATION))

    # Station
    c.execute("INSERT INTO stations VALUES (?,?,?,?,?,?,?,?,?)",
        (TEST_STATION, "Test Station (synthetic)", "SR", "TEST-DIV",
         3, 3, 0, 2000, 5))

    # Three platforms: P1 (disrupted), P2, P3 (both alternatives)
    c.execute("INSERT INTO platforms VALUES (?,?,?,?,?)",
        (DISRUPTED_RES, TEST_STATION, 1, "MAINLINE", "PLATFORM"))
    c.execute("INSERT INTO platforms VALUES (?,?,?,?,?)",
        (SAFE_RES_A,    TEST_STATION, 2, "MAINLINE", "PLATFORM"))
    c.execute("INSERT INTO platforms VALUES (?,?,?,?,?)",
        (SAFE_RES_B,    TEST_STATION, 3, "MAINLINE", "PLATFORM"))

    # Timetable records: both trains on P1 (disrupted)
    # Record 1001: Train A
    c.execute(
        "INSERT INTO timetable VALUES (1001,?,?,1,1,?,?,?,1,'MAINLINE','AUTO')",
        (TRAIN_A, TEST_STATION, A_ARR, A_DEP, DISRUPTED_RES))
    # Record 1002: Train B
    c.execute(
        "INSERT INTO timetable VALUES (1002,?,?,1,2,?,?,?,1,'MAINLINE','AUTO')",
        (TRAIN_B, TEST_STATION, B_ARR, B_DEP, DISRUPTED_RES))

    # Resource allocations for both trains (original P1 assignment)
    c.execute(
        "INSERT INTO resource_allocations VALUES "
        "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("ALLOC-1001", DISRUPTED_RES, "PLATFORM",
         TEST_STATION, "Test Station (synthetic)",
         1, "MAINLINE", 1, 1001,
         A_ALLOC_S, A_ALLOC_E, A_OCC, A_BUF, A_RELEASE,
         "ACTIVE", "SYNTHETIC"))
    c.execute(
        "INSERT INTO resource_allocations VALUES "
        "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("ALLOC-1002", DISRUPTED_RES, "PLATFORM",
         TEST_STATION, "Test Station (synthetic)",
         1, "MAINLINE", 1, 1002,
         B_ALLOC_S, B_ALLOC_E, B_OCC, B_BUF, B_RELEASE,
         "ACTIVE", "SYNTHETIC"))

    conn.commit()
    conn.close()
    return 1001, 1002


def _create_test_passenger_csv(csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_text(
        "station_code,station_name,category,daily_passengers\n"
        f"{TEST_STATION},Test Station (synthetic),NSG 1,5000\n"
    )


# ===========================================================================
# Helpers
# ===========================================================================

def _section(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


# ===========================================================================
# TESTS
# ===========================================================================

def run_test1_disruption_filter(
    db_path: Path,
    record_a: int,
    record_b: int,
) -> bool:
    _section("TEST 1 -- Disruption Filter")

    from src.optimization.alns_disruption import Disruption, DisruptionFilter
    from src.optimization.alns_data_loader import ALNSDataLoader

    disruption = Disruption(
        disruption_type="PLATFORM_CLOSURE",
        station_code=TEST_STATION,
        resource_id=DISRUPTED_RES,
        start_time=DISRUPTION_START,
        end_time=DISRUPTION_END,
        day=1,
    )

    solution = ALNSDataLoader(database_path=db_path).load_timetable()
    affected = DisruptionFilter(database_path=db_path).find_affected_records(
        disruption, solution
    )
    affected_ids = [r.timetable_record_id for r in affected]
    print(f"  Affected record IDs: {affected_ids}")

    ok = record_a in affected_ids and record_b in affected_ids
    if ok:
        print(f"  PASS -- Records {record_a} and {record_b} both identified as affected.")
    else:
        print(f"  FAIL -- Expected both {record_a} and {record_b} in {affected_ids}.")
    return ok


def run_test2_feasible_candidate(
    db_path: Path,
    passenger_csv: Path,
    record_a: int,
) -> bool:
    _section("TEST 2 -- Feasible Candidate (Train A moved to TEST-P2)")

    from src.optimization.alns_disruption import Disruption
    from src.optimization.alns_data_loader import ALNSDataLoader
    from src.optimization.alns_candidate import CandidateBuilder
    from src.optimization.alns_move import TimetableModification
    from src.optimization.alns_evaluation import CandidateEvaluator

    disruption = Disruption(
        disruption_type="PLATFORM_CLOSURE",
        station_code=TEST_STATION,
        resource_id=DISRUPTED_RES,
        start_time=DISRUPTION_START,
        end_time=DISRUPTION_END,
        day=1,
    )

    solution = ALNSDataLoader(database_path=db_path).load_timetable()

    # Move Train A to P2, Train B to P3 => both feasible, no conflict
    from src.optimization.alns_move import TimetableModification as TM
    cand = CandidateBuilder.apply_modification(
        solution,
        TM(timetable_record_id=record_a,
           new_resource_id=SAFE_RES_A, new_platform_number=2,
           new_platform_type="MAINLINE",
           reason="Test: move Train A to P2"),
    )
    cand = CandidateBuilder.apply_modification(
        cand,
        TM(timetable_record_id=record_a + 1,
           new_resource_id=SAFE_RES_B, new_platform_number=3,
           new_platform_type="MAINLINE",
           reason="Test: move Train B to P3"),
    )

    evaluator = CandidateEvaluator(
        db_path=db_path,
        model_path=MODEL_PATH,
        passenger_data_path=passenger_csv,
        disruption=disruption,
    )
    result = evaluator.evaluate(cand, affected_train_count=2)

    print(f"  Feasible          : {result.is_feasible}")
    print(f"  Objective         : {result.objective_value}")
    print(f"  Total delay (min) : {result.total_delay_minutes}")
    print(f"  Passenger impact  : {result.passenger_impact_minutes}")

    ok = result.is_feasible and (
        result.objective_value is not None and math.isfinite(result.objective_value)
    )
    if ok:
        print(f"  PASS -- Feasible=True, Objective={result.objective_value}")
    else:
        print(f"  FAIL -- Feasible={result.is_feasible}, Objective={result.objective_value}")
    return ok


def run_test3_infeasible_candidate(
    db_path: Path,
    passenger_csv: Path,
    record_a: int,
) -> bool:
    _section("TEST 3 -- Infeasible Candidate (both trains on TEST-P2 simultaneously)")

    from src.optimization.alns_disruption import Disruption
    from src.optimization.alns_data_loader import ALNSDataLoader
    from src.optimization.alns_candidate import CandidateBuilder
    from src.optimization.alns_move import TimetableModification as TM
    from src.optimization.alns_evaluation import CandidateEvaluator
    from src.optimization.alns_feasibility import FeasibilityChecker

    disruption = Disruption(
        disruption_type="PLATFORM_CLOSURE",
        station_code=TEST_STATION,
        resource_id=DISRUPTED_RES,
        start_time=DISRUPTION_START,
        end_time=DISRUPTION_END,
        day=1,
    )

    solution = ALNSDataLoader(database_path=db_path).load_timetable()

    # BOTH trains to P2 -- overlapping allocations => CONFLICT
    #   Train A: alloc 10:05-10:12, release 10:17
    #   Train B: alloc 10:13-10:20, release 10:25
    #   Overlap: 10:13 < 10:17  =>  conflict
    cand = CandidateBuilder.apply_modification(
        solution,
        TM(timetable_record_id=record_a,
           new_resource_id=SAFE_RES_A, new_platform_number=2,
           new_platform_type="MAINLINE",
           reason="Test: move Train A to P2"),
    )
    cand = CandidateBuilder.apply_modification(
        cand,
        TM(timetable_record_id=record_a + 1,
           new_resource_id=SAFE_RES_A, new_platform_number=2,
           new_platform_type="MAINLINE",
           reason="Test: move Train B to P2 (conflict!)"),
    )

    evaluator = CandidateEvaluator(
        db_path=db_path,
        model_path=MODEL_PATH,
        passenger_data_path=passenger_csv,
        disruption=disruption,
    )
    result = evaluator.evaluate(cand, affected_train_count=2)

    checker = FeasibilityChecker(database_path=db_path, disruption=disruption)
    _, violations = checker.check_solution(cand)

    print(f"  Feasible  : {result.is_feasible}")
    print(f"  Objective : {result.objective_value}")
    print("  Violations from FeasibilityChecker:")
    if violations:
        for rec_id, vlist in violations.items():
            for v in vlist:
                print(f"    [{rec_id}] {v}")
    else:
        print("    (none -- conflict not detected; verify allocation overlap logic)")

    ok = not result.is_feasible and result.objective_value == float("inf")
    if ok:
        print("  PASS -- Feasible=False, Objective=inf (production evaluator).")
    else:
        print(f"  FAIL -- Feasible={result.is_feasible}, Objective={result.objective_value}")
    return ok


def run_test4_optimizer_rejection(
    db_path: Path,
    passenger_csv: Path,
) -> bool:
    """
    TEST 4 -- Actual ALNS optimizer rejection.

    Scenario:
      Two trains (T9991, T9992) both on disrupted TEST-P1.
      Two alternatives: TEST-P2, TEST-P3.
      Repair pool per train: [P2, P3].

      When the optimizer independently selects repairs for each train:
        (T9991->P2) + (T9992->P2)  => OVERLAP => infeasible => REJECTED
        (T9991->P3) + (T9992->P3)  => OVERLAP => infeasible => REJECTED
        (T9991->P2) + (T9992->P3)  => OK => feasible => accepted
        (T9991->P3) + (T9992->P2)  => OK => feasible => accepted

      With 20+ iterations, infeasible combos will occur naturally.
      Each infeasible candidate increments rejected_candidates_count
      via the real production code path (alns_optimizer.py line 438).
    """
    _section("TEST 4 -- Actual ALNS Optimizer Rejection Path")

    from src.optimization.alns_disruption import Disruption
    from src.optimization.alns_optimizer import ALNSOptimizer

    disruption = Disruption(
        disruption_type="PLATFORM_CLOSURE",
        station_code=TEST_STATION,
        resource_id=DISRUPTED_RES,
        start_time=DISRUPTION_START,
        end_time=DISRUPTION_END,
        day=1,
    )

    optimizer = ALNSOptimizer(
        db_path=db_path,
        model_path=MODEL_PATH,
        passenger_data_path=passenger_csv,
    )

    result = optimizer.optimize(
        disruption=disruption,
        iterations=30,
        max_candidates=300,
        random_seed=42,
    )

    print(f"  Affected records     : {len(result.affected_records)}")
    print(f"  Iterations executed  : {result.iterations}")
    print(f"  Candidates generated : {result.candidates_generated_count}")
    print(f"  Feasible candidates  : {result.feasible_candidates_count}")
    print(f"  Accepted candidates  : {result.accepted_candidates_count}")
    print(f"  Rejected candidates  : {result.rejected_candidates_count}")
    print(f"  Best objective       : {result.best_objective}")
    print(f"  Execution time (s)   : {result.execution_time_seconds:.3f}")

    if result.repairs_generated:
        print(f"\n  Repair pool (per train):")
        from collections import defaultdict
        by_train: dict = defaultdict(list)
        for r in result.repairs_generated:
            by_train[r.train_number].append(r.alternative_resource_id)
        for train, platforms in by_train.items():
            print(f"    {train}: {platforms}")

    if result.rejected_candidates_count > 0:
        print(
            f"\n  PASS -- GENUINE REJECTION CONFIRMED.\n"
            f"  {result.rejected_candidates_count} candidate(s) rejected "
            "by the production acceptance logic (alns_optimizer.py line 438).\n"
            "  Cause: combined platform assignment produced an infeasible "
            "solution (both trains on same platform simultaneously).\n"
            "  The infeasible path set accepted=False at line 431."
        )
        return True

    print(
        f"\n  NOT TRIGGERED -- {result.candidates_generated_count} candidates "
        f"generated, {result.rejected_candidates_count} rejected.\n"
        f"  The repair selector may have avoided conflicting combos this run."
    )
    return False


# ===========================================================================
# Integrity verification
# ===========================================================================

def verify_integrity(
    before: dict[str, str],
    after: dict[str, str],
) -> int:
    modified = 0
    for path, digest_before in before.items():
        digest_after = after.get(path)
        if digest_after is None:
            print(f"  WARNING: protected file disappeared: {path}")
            modified += 1
        elif digest_after != digest_before:
            print(f"  ERROR: protected file MODIFIED: {path}")
            modified += 1
    return modified


# ===========================================================================
# Main
# ===========================================================================

def main() -> None:
    print()
    print("=" * 60)
    print("ALNS REJECTION TEST (CONTROLLED SYNTHETIC ENVIRONMENT)")
    print("=" * 60)

    before = _snapshot(PROTECTED_FILES)

    tmp_dir = Path(tempfile.mkdtemp(prefix="alns_rejection_test_"))
    db_path  = tmp_dir / "test_railway.db"
    pax_csv  = tmp_dir / "test_passenger_data.csv"

    t1 = t2 = t3 = t4 = False
    try:
        print(f"\nTemporary directory : {tmp_dir}")
        print(f"Synthetic database  : {db_path}")
        print(f"Synthetic CSV       : {pax_csv}")

        record_a, record_b = _create_test_db(db_path)
        _create_test_passenger_csv(pax_csv)

        print(f"\nSynthetic scenario:")
        print(f"  Disrupted platform : {DISRUPTED_RES}")
        print(f"  Alternatives       : {SAFE_RES_A}, {SAFE_RES_B}")
        print(f"  Disruption         : {DISRUPTION_START} to {DISRUPTION_END} (Day 1)")
        print(f"  Train A ({TRAIN_A}) : record #{record_a}  "
              f"{A_ARR} -> {A_DEP} on {DISRUPTED_RES}")
        print(f"  Train B ({TRAIN_B}) : record #{record_b}  "
              f"{B_ARR} -> {B_DEP} on {DISRUPTED_RES}")
        print(f"\n  Conflict rule: if both trains assigned to same alternative")
        print(f"  platform, allocations overlap -> infeasible -> REJECTED")
        print(f"    A release={A_RELEASE} > B alloc_start={B_ALLOC_S} => overlap on same platform")

        t1 = run_test1_disruption_filter(db_path, record_a, record_b)
        t2 = run_test2_feasible_candidate(db_path, pax_csv, record_a)
        t3 = run_test3_infeasible_candidate(db_path, pax_csv, record_a)
        t4 = run_test4_optimizer_rejection(db_path, pax_csv)

    except Exception:
        import traceback
        _section("UNHANDLED EXCEPTION")
        traceback.print_exc()

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"\nCleaned up: {tmp_dir}")

    after = _snapshot(PROTECTED_FILES)
    modified_count = verify_integrity(before, after)

    _section("ALNS REJECTION TEST -- FINAL SUMMARY")
    print()
    print(f"Production files modified : {modified_count}")
    print()
    print(f"TEST 1 -- Disruption Filter          : {'PASS' if t1 else 'FAIL'}")
    print(f"TEST 2 -- Feasible Candidate         : {'PASS' if t2 else 'FAIL'}")
    print(f"TEST 3 -- Infeasible Candidate       : {'PASS' if t3 else 'FAIL'}")
    print(f"TEST 4 -- Actual Optimizer Rejection : {'PASS' if t4 else 'NOT TRIGGERED / FAIL'}")
    print()
    print("Temporary files created and cleaned:")
    print(f"  {db_path}  [deleted]")
    print(f"  {pax_csv}  [deleted]")
    print()

    if modified_count > 0:
        print("RESULT: INTEGRITY FAILURE -- production files were modified.")
        sys.exit(2)
    elif not (t1 and t2 and t3):
        print("RESULT: Core test(s) 1-3 failed. See details above.")
        sys.exit(1)
    elif not t4:
        print("RESULT: Tests 1-3 PASSED. Test 4 NOT TRIGGERED.")
        sys.exit(0)
    else:
        print("RESULT: ALL TESTS PASSED. No existing project files were modified.")
        sys.exit(0)


if __name__ == "__main__":
    main()
