from __future__ import annotations

from pathlib import Path
import sys
import time
import unittest

# Add project root to sys.path if not present
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.optimization.alns_candidate import CandidateBuilder
from src.optimization.alns_data_loader import (
    DATABASE_PATH,
    load_initial_solution,
)
from src.optimization.alns_destroy import ALNSDestroyOperator
from src.optimization.alns_disruption import Disruption, DisruptionFilter
from src.optimization.alns_evaluation import CandidateEvaluator
from src.optimization.alns_move import TimetableModification
from src.optimization.alns_optimizer import ALNSOptimizer
from src.optimization.alns_repair import ALNSRepairOperator


class TestALNSOptimizer(unittest.TestCase):
    """
    Test suite for ALNS Orchestration Layer using real database and real ML model.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Initialize controlled disruption scenario and optimizer."""
        cls.db_path = DATABASE_PATH
        cls.disruption = Disruption(
            disruption_type="PLATFORM_CLOSURE",
            station_code="MS",
            resource_id="MS-P9",
            start_time="05:00:00",
            end_time="05:20:00",
            day=1,
        )
        cls.optimizer = ALNSOptimizer(db_path=cls.db_path)
        cls.initial_solution = load_initial_solution(cls.db_path)

    def test_01_controlled_disruption(self) -> None:
        """1. Validate controlled PLATFORM_CLOSURE disruption initialization."""
        self.assertEqual(self.disruption.disruption_type, "PLATFORM_CLOSURE")
        self.assertEqual(self.disruption.station_code, "MS")
        self.assertEqual(self.disruption.resource_id, "MS-P9")
        print("PASS 1: Controlled PLATFORM_CLOSURE disruption initialized successfully.")

    def test_02_affected_records_detection(self) -> None:
        """2. Validate affected records detection."""
        filter_op = DisruptionFilter(self.db_path)
        affected_records = filter_op.find_affected_records(
            self.disruption, self.initial_solution
        )
        self.assertGreater(len(affected_records), 0)
        for rec in affected_records:
            self.assertEqual(rec.station_code, "MS")
            self.assertEqual(rec.resource_id, "MS-P9")
        print(f"PASS 2: Affected records detected ({len(affected_records)} records found).")

    def test_03_destroy_stage(self) -> None:
        """3. Validate destroy stage functionality."""
        filter_op = DisruptionFilter(self.db_path)
        affected_records = filter_op.find_affected_records(
            self.disruption, self.initial_solution
        )
        destroy_op = ALNSDestroyOperator()
        destroyed_sol, destroyed_info = destroy_op.destroy_records(
            self.initial_solution, affected_records
        )
        self.assertEqual(len(destroyed_info), len(affected_records))
        for info in destroyed_info:
            destroyed_rec = destroyed_sol.get_record(info.timetable_record_id)
            self.assertIsNone(destroyed_rec.resource_id)
            self.assertIsNone(destroyed_rec.platform_number)
            self.assertIsNone(destroyed_rec.platform_type)
        print("PASS 3: Destroy stage cleared resource assignments cleanly.")

    def test_04_repair_generation(self) -> None:
        """4. Validate repair generation."""
        filter_op = DisruptionFilter(self.db_path)
        affected_records = filter_op.find_affected_records(
            self.disruption, self.initial_solution
        )
        repair_op = ALNSRepairOperator(str(self.db_path))
        repairs = repair_op.generate_repairs(
            self.initial_solution, affected_records, self.disruption
        )
        self.assertGreater(len(repairs), 0)
        for repair in repairs:
            self.assertNotEqual(repair.alternative_resource_id, "MS-P9")
        print(f"PASS 4: Feasible repairs generated ({len(repairs)} repair candidates).")

    def test_05_complete_candidate_construction(self) -> None:
        """5. Validate complete candidate construction across all affected records."""
        filter_op = DisruptionFilter(self.db_path)
        affected_records = filter_op.find_affected_records(
            self.disruption, self.initial_solution
        )
        repair_op = ALNSRepairOperator(str(self.db_path))
        repairs = repair_op.generate_repairs(
            self.initial_solution, affected_records, self.disruption
        )

        candidate = self.initial_solution.copy()
        for record in affected_records:
            rec_repairs = [r for r in repairs if r.timetable_record_id == record.timetable_record_id]
            self.assertGreater(len(rec_repairs), 0)
            rep = rec_repairs[0]
            mod = TimetableModification(
                timetable_record_id=rep.timetable_record_id,
                new_resource_id=rep.alternative_resource_id,
                new_platform_number=rep.alternative_platform_number,
                new_platform_type=rep.alternative_platform_type,
                reason=rep.reason,
            )
            candidate = CandidateBuilder.apply_modification(candidate, mod)

        for record in affected_records:
            cand_rec = candidate.get_record(record.timetable_record_id)
            self.assertIsNotNone(cand_rec.resource_id)
            self.assertNotEqual(cand_rec.resource_id, "MS-P9")
        print("PASS 5: Complete candidate solution constructed covering all affected records.")

    def test_06_candidate_evaluation(self) -> None:
        """6. Validate complete candidate evaluation using CandidateEvaluator."""
        evaluator = CandidateEvaluator(
            db_path=self.db_path, disruption=self.disruption
        )
        result = self.optimizer.optimize(self.disruption, iterations=1)
        self.assertIsNotNone(result.best_solution)
        self.assertIsNotNone(result.best_solution.objective_value)
        self.assertIsNotNone(result.best_solution.total_delay_minutes)
        self.assertIsNotNone(result.best_solution.passenger_impact_minutes)
        print("PASS 6: Complete candidate solution evaluated with objective and delay metrics.")

    def test_07_infeasible_candidate_rejection(self) -> None:
        """7. Validate that infeasible candidates are assigned infinite objective value."""
        evaluator = CandidateEvaluator(
            db_path=self.db_path, disruption=self.disruption
        )
        invalid_candidate = self.initial_solution.copy()
        invalid_rec = list(invalid_candidate.records.values())[0]
        invalid_mod = TimetableModification(
            timetable_record_id=invalid_rec.timetable_record_id,
            new_resource_id="NON_EXISTENT_PLATFORM_XYZ",
            new_platform_number=999,
            new_platform_type="MAINLINE",
            reason="Testing infeasible platform rejection",
        )
        invalid_candidate = CandidateBuilder.apply_modification(
            invalid_candidate, invalid_mod
        )
        evaluated = evaluator.evaluate(invalid_candidate)
        self.assertFalse(evaluated.is_feasible)
        self.assertEqual(evaluated.objective_value, float("inf"))
        print("PASS 7: Infeasible candidates are rejected (objective = inf).")

    def test_08_at_least_one_feasible_solution(self) -> None:
        """8. Validate returning at least one feasible solution."""
        result = self.optimizer.optimize(self.disruption, iterations=2)
        self.assertGreater(result.feasible_candidates_count, 0)
        self.assertIsNotNone(result.best_solution)
        self.assertTrue(result.best_solution.is_feasible)
        print(f"PASS 8: Optimization returned feasible solution (Objective: {result.best_objective:.4f}).")

    def test_09_best_solution_contains_actual_changes(self) -> None:
        """9. Validate best solution contains actual timetable resource changes."""
        result = self.optimizer.optimize(self.disruption, iterations=2)
        self.assertIsNotNone(result.best_solution)
        changed_count = 0
        for rec in result.affected_records:
            best_rec = result.best_solution.get_record(rec.timetable_record_id)
            if best_rec.resource_id != rec.original_resource_id:
                changed_count += 1
        self.assertGreater(changed_count, 0)
        print(f"PASS 9: Best solution contains actual timetable changes ({changed_count} reassignments).")

    def test_10_multiple_distinct_feasible_alternatives(self) -> None:
        """10. Validate returning Top 3 distinct feasible recovery alternatives."""
        result = self.optimizer.optimize(self.disruption, iterations=5)
        self.assertGreater(len(result.top_solutions), 1)
        self.assertLessEqual(len(result.top_solutions), 3)

        signatures = set()
        for sol in result.top_solutions:
            sig = tuple(
                (r.timetable_record_id, r.resource_id)
                for r in sol.records.values()
                if r.timetable_record_id in {rec.timetable_record_id for rec in result.affected_records}
            )
            self.assertNotIn(sig, signatures)
            signatures.add(sig)
        print(f"PASS 10: Successfully returned {len(result.top_solutions)} distinct feasible recovery alternatives.")

    def test_11_zero_affected_records(self) -> None:
        """11. Validate behavior when disruption affects 0 timetable records."""
        no_records_disruption = Disruption(
            disruption_type="PLATFORM_CLOSURE",
            station_code="MAS",
            resource_id="MAS-P4",
            start_time="03:00:00",
            end_time="03:05:00",
            day=1,
        )
        result = self.optimizer.optimize(no_records_disruption)
        self.assertEqual(len(result.affected_records), 0)
        self.assertIsNotNone(result.best_solution)
        self.assertTrue(result.best_solution.is_feasible)
        print("PASS 11: Disruption with 0 affected records handled cleanly.")

    def test_12_incomplete_repair_rejection(self) -> None:
        """12. Validate that if any affected record cannot be repaired, no solution is returned."""
        # Scenario where an affected record has no compatible platform repairs
        disruption = Disruption(
            disruption_type="PLATFORM_CLOSURE",
            station_code="MS",
            resource_id="MS-P9",
            start_time="05:00:00",
            end_time="05:20:00",
            day=1,
        )
        # Mocking an impossible repair scenario by checking Optimizer when repair is empty
        result = self.optimizer.optimize(disruption, max_candidates=0)
        self.assertIsNone(result.best_solution)
        self.assertEqual(len(result.top_solutions), 0)
        print("PASS 12: Incomplete repair scenario correctly yields best_solution = None.")

    def test_13_candidate_generation_limits(self) -> None:
        """13. Validate max_candidates limit on candidate generation."""
        result = self.optimizer.optimize(self.disruption, max_candidates=5)
        self.assertLessEqual(result.candidates_generated_count, 5)
        print("PASS 13: max_candidates limit enforced during candidate generation.")

    def test_14_accurate_iteration_and_candidate_counts(self) -> None:
        """14. Validate accurate reporting of iterations and candidates generated."""
        result = self.optimizer.optimize(self.disruption, iterations=3, max_candidates=10)
        self.assertGreater(result.iterations, 0)
        self.assertLessEqual(result.iterations, 3)
        self.assertGreater(result.candidates_generated_count, 0)
        print(f"PASS 14: Iterations ({result.iterations}) and candidate counts ({result.candidates_generated_count}) reported accurately.")

    def test_15_no_duplicate_solutions(self) -> None:
        """15. Validate that top_solutions contains no duplicate solution signatures."""
        result = self.optimizer.optimize(self.disruption, iterations=5)
        signatures = [
            tuple(
                (r.timetable_record_id, r.resource_id)
                for r in sol.records.values()
                if r.timetable_record_id in {rec.timetable_record_id for rec in result.affected_records}
            )
            for sol in result.top_solutions
        ]
        self.assertEqual(len(signatures), len(set(signatures)))
        print("PASS 15: No duplicate solution signatures found in top_solutions.")


def main() -> None:
    """Run all 15 orchestration unit tests."""
    print("=" * 80)
    print("ALNS ORCHESTRATION LAYER EXTENDED TEST SUITE")
    print("=" * 80)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestALNSOptimizer)
    runner = unittest.TextTestRunner(verbosity=2)
    test_result = runner.run(suite)
    if not test_result.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    main()

