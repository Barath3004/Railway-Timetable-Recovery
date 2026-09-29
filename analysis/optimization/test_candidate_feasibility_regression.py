from __future__ import annotations

from pathlib import Path
import sys
import unittest

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.optimization.alns_candidate import CandidateBuilder
from src.optimization.alns_data_loader import DATABASE_PATH, load_initial_solution
from src.optimization.alns_feasibility import FeasibilityChecker
from src.optimization.alns_move import TimetableModification
from src.optimization.alns_solution import ALNSSolution, TimetableRecord


class TestCandidateFeasibilityRegression(unittest.TestCase):
    """Regression test suite for corrected ALNS feasibility checker."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.db_path = DATABASE_PATH
        cls.checker = FeasibilityChecker(database_path=cls.db_path)
        cls.initial_solution = load_initial_solution(cls.db_path)

    def test_01_two_modified_records_overlapping_conflict(self) -> None:
        """Verify that two modified records assigned to the same platform at overlapping times are flagged as infeasible."""
        solution = self.initial_solution.copy()
        record_ids = list(solution.records.keys())[:2]
        rec1 = solution.get_record(record_ids[0])
        rec2 = solution.get_record(record_ids[1])

        # Assign both to MS-P1 on Day 1 at overlapping times (08:00 -> 08:30)
        mod1 = TimetableModification(
            timetable_record_id=rec1.timetable_record_id,
            new_resource_id="MS-P1",
            new_platform_number=1,
            new_arrival="08:00:00",
            new_departure="08:30:00",
        )
        mod2 = TimetableModification(
            timetable_record_id=rec2.timetable_record_id,
            new_resource_id="MS-P1",
            new_platform_number=1,
            new_arrival="08:15:00",
            new_departure="08:45:00",
        )
        solution = CandidateBuilder.apply_modification(solution, mod1)
        solution = CandidateBuilder.apply_modification(solution, mod2)

        # Force record days to 1 for this test
        solution.get_record(rec1.timetable_record_id).day = 1
        solution.get_record(rec2.timetable_record_id).day = 1
        solution.get_record(rec1.timetable_record_id).station_code = "MS"
        solution.get_record(rec2.timetable_record_id).station_code = "MS"

        is_feasible, violations = self.checker.check_solution(solution)
        self.assertFalse(is_feasible)
        print("PASS 1: Two modified records overlapping on the same platform flagged as INFEASIBLE.")

    def test_02_two_modified_records_non_overlapping_feasible(self) -> None:
        """Verify that two modified records assigned to the same platform at non-overlapping times are feasible."""
        solution = self.initial_solution.copy()
        records = [r for r in solution.records.values() if r.station_code == "MS"][:2]
        rec1, rec2 = records[0], records[1]

        # Assign both to MS-P1 at non-overlapping times during an early morning window (02:00->02:15 and 03:00->03:15)
        mod1 = TimetableModification(
            timetable_record_id=rec1.timetable_record_id,
            new_resource_id="MS-P1",
            new_platform_number=1,
            new_arrival="02:00:00",
            new_departure="02:15:00",
        )
        mod2 = TimetableModification(
            timetable_record_id=rec2.timetable_record_id,
            new_resource_id="MS-P1",
            new_platform_number=1,
            new_arrival="03:00:00",
            new_departure="03:15:00",
        )
        solution = CandidateBuilder.apply_modification(solution, mod1)
        solution = CandidateBuilder.apply_modification(solution, mod2)
        solution.get_record(rec1.timetable_record_id).day = 1
        solution.get_record(rec2.timetable_record_id).day = 1

        rec1_feasible, rec1_viols = self.checker.check_record(solution.get_record(rec1.timetable_record_id), solution)
        rec2_feasible, rec2_viols = self.checker.check_record(solution.get_record(rec2.timetable_record_id), solution)
        self.assertTrue(rec1_feasible, f"rec1 violations: {rec1_viols}")
        self.assertTrue(rec2_feasible, f"rec2 violations: {rec2_viols}")
        print("PASS 2: Two modified records non-overlapping on the same platform are FEASIBLE.")

    def test_03_obsolete_database_allocation_excluded(self) -> None:
        """Verify that a modified train's obsolete original database allocation is excluded from conflict checking."""
        solution = self.initial_solution.copy()
        # Pick record 9033 (originally MAS-P4)
        rec1 = solution.get_record(9033)

        # Reassign rec1 away from MAS-P4 to MAS-P5
        mod1 = TimetableModification(
            timetable_record_id=rec1.timetable_record_id,
            new_resource_id="MAS-P5",
            new_platform_number=5,
            new_platform_type="MAINLINE",
        )
        solution = CandidateBuilder.apply_modification(solution, mod1)

        # Pick another train rec2 and assign it to MAS-P4 during rec1's original time slot
        # Using early morning 02:00 window where MAS-P4 has no other baseline trains
        rec2_id = [r.timetable_record_id for r in solution.records.values() if r.timetable_record_id != 9033 and r.station_code == "MAS"][0]
        rec2 = solution.get_record(rec2_id)
        rec2.arrival = rec1.original_arrival
        rec2.departure = rec1.original_departure

        mod2 = TimetableModification(
            timetable_record_id=rec2.timetable_record_id,
            new_resource_id="MAS-P4",
            new_platform_number=4,
            new_arrival=rec1.original_arrival,
            new_departure=rec1.original_departure,
        )
        solution = CandidateBuilder.apply_modification(solution, mod2)

        # Check conflict specifically against rec1's obsolete original allocation
        has_conflict, conflicts = self.checker.check_platform_conflict(
            rec2, self.checker.get_candidate_allocation(rec2), solution
        )
        rec1_obsolete_conflict = any(str(rec1.timetable_record_id) in c for c in conflicts)
        self.assertFalse(rec1_obsolete_conflict, f"Obsolete allocation of rec1 was not excluded: {conflicts}")
        print("PASS 3: Obsolete baseline allocation of modified train successfully EXCLUDED.")

    def test_04_candidate_timing_departure_only(self) -> None:
        """Verify candidate timing calculation for departure-only records."""
        solution = self.initial_solution.copy()
        rec = TimetableRecord(
            timetable_record_id=9033,
            train_number="TEST1",
            station_code="MAS",
            day=1,
            stop_number=1,
            arrival=None,
            departure="10:00:00",
            resource_id="MAS-P5",
            platform_number=5,
            platform_type="MAINLINE",
            original_arrival=None,
            original_departure="08:00:00",
            original_resource_id="MAS-P4",
            original_platform_number=4,
        )
        solution.add_record(rec)
        alloc = self.checker.get_candidate_allocation(rec)
        self.assertEqual(alloc.allocation_end, "10:00:00")
        print("PASS 4: Candidate timing for departure-only record correctly calculated.")

    def test_05_midnight_crossing_and_day_handling(self) -> None:
        """Verify cross-midnight, adjacent-day, and touching-at-release-time overlap checking."""
        # 1. Touching exactly at release time -> No overlap
        self.assertFalse(
            self.checker._intervals_overlap(1, "10:00:00", "11:00:00", 1, "11:00:00", "12:00:00")
        )
        # 2. Same-day overlap -> Overlap
        self.assertTrue(
            self.checker._intervals_overlap(1, "10:00:00", "11:30:00", 1, "11:00:00", "12:00:00")
        )
        # 3. Same-day non-overlap -> No overlap
        self.assertFalse(
            self.checker._intervals_overlap(1, "10:00:00", "11:00:00", 1, "12:00:00", "13:00:00")
        )
        # 4. Midnight crossing Day 1 (23:50 -> 00:20) and Day 2 (00:10 -> 01:00) -> Overlap
        self.assertTrue(
            self.checker._intervals_overlap(1, "23:50:00", "00:20:00", 2, "00:10:00", "01:00:00")
        )
        # 5. Different days, no midnight overlap -> No overlap
        self.assertFalse(
            self.checker._intervals_overlap(1, "10:00:00", "11:00:00", 2, "10:00:00", "11:00:00")
        )
        print("PASS 5: Midnight crossing and day handling verified across all test cases.")

    def test_06_unrepaired_record_rejection(self) -> None:
        """Verify that an affected record with resource_id = None is rejected as infeasible."""
        solution = self.initial_solution.copy()
        rec = solution.get_record(9033)
        rec.resource_id = None
        rec.platform_number = None

        is_feasible, violations = self.checker.check_solution(solution)
        self.assertFalse(is_feasible)
        self.assertIn(9033, violations)
        print("PASS 6: Affected record with resource_id = None rejected as INFEASIBLE.")


def main() -> None:
    print("=" * 80)
    print("ALNS FEASIBILITY CHECKER REGRESSION TEST SUITE")
    print("=" * 80)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCandidateFeasibilityRegression)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    main()
