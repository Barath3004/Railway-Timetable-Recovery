from __future__ import annotations

from dataclasses import dataclass, field
import itertools
import math
from pathlib import Path
import random
import time
from typing import Any

from src.optimization.alns_candidate import CandidateBuilder
from src.optimization.alns_data_loader import (
    DATABASE_PATH,
    load_initial_solution,
)
from src.optimization.alns_destroy import ALNSDestroyOperator
from src.optimization.alns_disruption import Disruption, DisruptionFilter
from src.optimization.alns_evaluation import (
    MODEL_PATH,
    PASSENGER_DATA_PATH,
    CandidateEvaluator,
)
from src.optimization.alns_move import TimetableModification
from src.optimization.alns_repair import ALNSRepairOperator, RepairCandidate
from src.optimization.alns_solution import ALNSSolution, TimetableRecord


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class ALNSOptimizationResult:
    """Stores the complete output of an ALNS optimization run."""

    disruption: Disruption
    affected_records: list[TimetableRecord] = field(default_factory=list)
    iterations: int = 0
    candidates_generated_count: int = 0
    feasible_candidates_count: int = 0
    best_solution: ALNSSolution | None = None
    best_objective: float | None = None
    best_total_delay: float | None = None
    best_passenger_impact: float | None = None
    top_solutions: list[ALNSSolution] = field(default_factory=list)
    repairs_generated: list[RepairCandidate] = field(default_factory=list)
    execution_time_seconds: float = 0.0

    # Diagnostic ALNS metadata fields
    destroy_operator_usage: dict[str, int] = field(default_factory=dict)
    repair_operator_usage: dict[str, int] = field(default_factory=dict)
    destroy_operator_weights: dict[str, float] = field(default_factory=dict)
    repair_operator_weights: dict[str, float] = field(default_factory=dict)
    accepted_candidates_count: int = 0
    rejected_candidates_count: int = 0

    def get_summary(self) -> dict[str, Any]:
        """Return a dictionary summary of optimization results."""
        summary = {
            "disruption_type": self.disruption.disruption_type,
            "station_code": self.disruption.station_code,
            "resource_id": self.disruption.resource_id,
            "disruption_time": f"{self.disruption.start_time} -> {self.disruption.end_time}",
            "iterations": self.iterations,
            "affected_record_count": len(self.affected_records),
            "candidates_generated": self.candidates_generated_count,
            "feasible_candidates": self.feasible_candidates_count,
            "best_objective": self.best_objective,
            "best_total_delay_minutes": self.best_total_delay,
            "best_passenger_impact_minutes": self.best_passenger_impact,
            "top_solutions_count": len(self.top_solutions),
            "execution_time_seconds": round(self.execution_time_seconds, 4),
        }
        if self.destroy_operator_weights:
            summary["destroy_operator_weights"] = {
                k: round(v, 4) for k, v in self.destroy_operator_weights.items()
            }
        if self.repair_operator_weights:
            summary["repair_operator_weights"] = {
                k: round(v, 4) for k, v in self.repair_operator_weights.items()
            }
        return summary


class ALNSOptimizer:
    """
    Orchestration layer for ALNS timetable recovery.

    Integrates:
    - ALNSDataLoader (initial solution loading)
    - DisruptionFilter (identifying affected timetable records)
    - ALNSDestroyOperator (destroying affected resource assignments)
    - ALNSRepairOperator (generating feasible platform repair candidates)
    - CandidateBuilder (constructing complete candidate solutions)
    - CandidateEvaluator (delay + passenger impact evaluation and feasibility checking)

    Performs iterative Adaptive Large Neighborhood Search maintaining a current solution,
    updating operator weights dynamically, applying Simulated Annealing acceptance,
    tracking global best solution, and returning Top 3 distinct feasible recovery alternatives.
    """

    def __init__(
        self,
        db_path: Path | str = DATABASE_PATH,
        model_path: Path | str = MODEL_PATH,
        passenger_data_path: Path | str = PASSENGER_DATA_PATH,
        delay_weight: float = 0.5,
        passenger_weight: float = 0.5,
    ) -> None:
        self.db_path = Path(db_path)
        self.model_path = Path(model_path)
        self.passenger_data_path = Path(passenger_data_path)
        self.delay_weight = delay_weight
        self.passenger_weight = passenger_weight

    def optimize(
        self,
        disruption: Disruption,
        iterations: int = 10,
        max_candidates: int = 500,
        random_seed: int | None = 42,
    ) -> ALNSOptimizationResult:
        """
        Execute genuine ALNS timetable recovery optimization for an active disruption.
        """
        start_time = time.time()

        # Step 1: Load initial solution
        initial_solution = load_initial_solution(self.db_path)

        # Step 2: Identify affected records
        disruption_filter = DisruptionFilter(self.db_path)
        affected_records = disruption_filter.find_affected_records(
            disruption, initial_solution
        )

        if not affected_records:
            elapsed = time.time() - start_time
            initial_solution.is_feasible = True
            initial_solution.objective_value = 0.0
            return ALNSOptimizationResult(
                disruption=disruption,
                affected_records=[],
                iterations=iterations,
                candidates_generated_count=0,
                feasible_candidates_count=1,
                best_solution=initial_solution,
                best_objective=0.0,
                best_total_delay=0.0,
                best_passenger_impact=0.0,
                top_solutions=[initial_solution],
                execution_time_seconds=elapsed,
            )

        # Step 3: Initialize evaluator
        evaluator = CandidateEvaluator(
            db_path=self.db_path,
            model_path=self.model_path,
            passenger_data_path=self.passenger_data_path,
            disruption=disruption,
            delay_weight=self.delay_weight,
            passenger_weight=self.passenger_weight,
        )

        # Step 4: Initialize Destroy and Repair operators
        destroy_operator = ALNSDestroyOperator()
        repair_operator = ALNSRepairOperator(str(self.db_path))

        # Step 5: Generate feasible repair pool per affected record
        repairs = repair_operator.generate_repairs(
            initial_solution, affected_records, disruption
        )

        repairs_by_record: dict[int, list[RepairCandidate]] = {}
        for record in affected_records:
            rec_id = record.timetable_record_id
            rec_repairs = [r for r in repairs if r.timetable_record_id == rec_id]
            repairs_by_record[rec_id] = rec_repairs

        # Reject if any affected record has no feasible repairs
        records_with_repairs = [
            record for record in affected_records if repairs_by_record[record.timetable_record_id]
        ]

        if len(records_with_repairs) < len(affected_records) or max_candidates <= 0:
            elapsed = time.time() - start_time
            return ALNSOptimizationResult(
                disruption=disruption,
                affected_records=affected_records,
                iterations=0,
                candidates_generated_count=0,
                feasible_candidates_count=0,
                best_solution=None,
                best_objective=None,
                best_total_delay=None,
                best_passenger_impact=None,
                top_solutions=[],
                repairs_generated=repairs,
                execution_time_seconds=elapsed,
            )

        affected_train_count = len(
            {record.train_number for record in affected_records}
        )

        # Construct initial feasible current solution
        destroyed_init, _ = destroy_operator.destroy_records(
            initial_solution, affected_records
        )
        candidate_init = destroyed_init.copy()
        for record in affected_records:
            first_rep = repairs_by_record[record.timetable_record_id][0]
            mod = TimetableModification(
                timetable_record_id=first_rep.timetable_record_id,
                new_resource_id=first_rep.alternative_resource_id,
                new_platform_number=first_rep.alternative_platform_number,
                new_platform_type=first_rep.alternative_platform_type,
                reason=first_rep.reason,
            )
            candidate_init = CandidateBuilder.apply_modification(
                candidate_init, mod
            )

        evaluated_init = evaluator.evaluate(
            candidate_init, affected_train_count=affected_train_count
        )

        feasible_solutions: list[ALNSSolution] = []
        current_solution: ALNSSolution | None = None
        best_solution: ALNSSolution | None = None
        best_objective: float | None = None

        if evaluated_init.is_feasible:
            current_solution = evaluated_init.copy()
            best_solution = current_solution.copy()
            best_objective = current_solution.objective_value
            feasible_solutions.append(evaluated_init)
        else:
            # Search repair combinations for a first feasible candidate
            repair_lists = [
                repairs_by_record[record.timetable_record_id]
                for record in affected_records
            ]
            for combo in itertools.islice(itertools.product(*repair_lists), max_candidates):
                cand = destroyed_init.copy()
                for rep in combo:
                    mod = TimetableModification(
                        timetable_record_id=rep.timetable_record_id,
                        new_resource_id=rep.alternative_resource_id,
                        new_platform_number=rep.alternative_platform_number,
                        new_platform_type=rep.alternative_platform_type,
                        reason=rep.reason,
                    )
                    cand = CandidateBuilder.apply_modification(cand, mod)
                eval_cand = evaluator.evaluate(
                    cand, affected_train_count=affected_train_count
                )
                if eval_cand.is_feasible:
                    current_solution = eval_cand.copy()
                    best_solution = current_solution.copy()
                    best_objective = current_solution.objective_value
                    feasible_solutions.append(eval_cand)
                    break

        if current_solution is None:
            elapsed = time.time() - start_time
            return ALNSOptimizationResult(
                disruption=disruption,
                affected_records=affected_records,
                iterations=0,
                candidates_generated_count=0,
                feasible_candidates_count=0,
                best_solution=None,
                best_objective=None,
                best_total_delay=None,
                best_passenger_impact=None,
                top_solutions=[],
                repairs_generated=repairs,
                execution_time_seconds=elapsed,
            )

        # Setup ALNS Adaptive Operators and Weights
        rng = random.Random(random_seed) if random_seed is not None else random.Random(42)

        destroy_ops = ["full_destroy", "partial_destroy"]
        repair_ops = [
            "standard_repair",
            "alternative_order_repair",
            "max_buffer_repair",
            "random_repair",
        ]

        destroy_weights = {op: 1.0 for op in destroy_ops}
        repair_weights = {op: 1.0 for op in repair_ops}
        destroy_usage = {op: 0 for op in destroy_ops}
        repair_usage = {op: 0 for op in repair_ops}

        accepted_candidates_count = 0
        rejected_candidates_count = 0
        candidates_generated_count = 0
        actual_iterations_executed = 0

        # Solution signature tracking for reward and top solution collection
        seen_signatures: set[tuple] = set()

        if current_solution is not None:
            init_sig = tuple(
                (rec.timetable_record_id, rec.resource_id)
                for rec in sorted(
                    current_solution.records.values(), key=lambda r: r.timetable_record_id
                )
                if rec.timetable_record_id in {r.timetable_record_id for r in affected_records}
            )
            seen_signatures.add(init_sig)

        # Simulated Annealing Temperature Setup
        init_val = current_solution.objective_value if current_solution.objective_value is not None else 1.0
        T_start = max(1.0, float(init_val) * 0.1)
        T_min = 0.001
        max_iters = max(1, int(iterations))
        cooling_rate = (T_min / T_start) ** (1.0 / max_iters) if T_start > T_min else 0.95
        T = T_start

        # Step 6-10: Genuine Iterative ALNS Search Loop
        for it in range(1, max_iters + 1):
            if candidates_generated_count >= max_candidates:
                break

            actual_iterations_executed += 1

            # Select destroy operator using adaptive weights
            d_names = list(destroy_weights.keys())
            d_wts = list(destroy_weights.values())
            sel_destroy = rng.choices(d_names, weights=d_wts)[0]
            destroy_usage[sel_destroy] += 1

            # Destroy stage
            if sel_destroy == "full_destroy":
                destroyed_sol, _ = destroy_operator.destroy_records(
                    current_solution, affected_records
                )
            else:
                destroyed_sol, _ = destroy_operator.destroy_partial(
                    current_solution, affected_records, rng=rng, ratio=0.5
                )

            # Select repair operator using adaptive weights
            r_names = list(repair_weights.keys())
            r_wts = list(repair_weights.values())
            sel_repair = rng.choices(r_names, weights=r_wts)[0]
            repair_usage[sel_repair] += 1

            # Repair stage for destroyed records
            candidate = destroyed_sol.copy()
            for rec_idx, record in enumerate(affected_records):
                rec_id = record.timetable_record_id
                cand_rec = candidate.get_record(rec_id)
                if cand_rec.resource_id is None:
                    rec_repairs = repairs_by_record[rec_id]
                    chosen_rep = repair_operator.select_repair_candidate(
                        rec_repairs,
                        strategy=sel_repair,
                        iteration_index=it - 1,
                        record_index=rec_idx,
                        rng=rng,
                    )
                    if chosen_rep is not None:
                        mod = TimetableModification(
                            timetable_record_id=chosen_rep.timetable_record_id,
                            new_resource_id=chosen_rep.alternative_resource_id,
                            new_platform_number=chosen_rep.alternative_platform_number,
                            new_platform_type=chosen_rep.alternative_platform_type,
                            reason=chosen_rep.reason,
                        )
                        candidate = CandidateBuilder.apply_modification(candidate, mod)

            # Candidate Evaluation
            candidate = evaluator.evaluate(
                candidate, affected_train_count=affected_train_count
            )
            candidates_generated_count += 1

            # Acceptance and Objective Comparison
            cand_obj = candidate.objective_value if (candidate.is_feasible and candidate.objective_value is not None) else float("inf")
            curr_obj = current_solution.objective_value if (current_solution and current_solution.objective_value is not None) else float("inf")

            accepted = False
            reward = 0.0

            if candidate.is_feasible:
                feasible_solutions.append(candidate)

                cand_sig = tuple(
                    (rec.timetable_record_id, rec.resource_id)
                    for rec in sorted(
                        candidate.records.values(), key=lambda r: r.timetable_record_id
                    )
                    if rec.timetable_record_id in {r.timetable_record_id for r in affected_records}
                )
                is_new_signature = cand_sig not in seen_signatures
                if is_new_signature:
                    seen_signatures.add(cand_sig)

                if best_solution is None or best_objective is None or cand_obj < best_objective:
                    best_solution = candidate.copy()
                    best_objective = cand_obj
                    accepted = True
                    reward = 10.0
                elif cand_obj < curr_obj:
                    accepted = True
                    reward = 5.0
                elif is_new_signature:
                    # Reward discovering a new distinct solution alternative
                    delta = cand_obj - curr_obj
                    prob = math.exp(-delta / T) if T > 1e-6 else 0.0
                    if rng.random() < prob:
                        accepted = True
                        reward = 4.0
                    else:
                        accepted = False
                        reward = 2.0
                else:
                    delta = cand_obj - curr_obj
                    prob = math.exp(-delta / T) if T > 1e-6 else 0.0
                    if rng.random() < prob:
                        accepted = True
                        reward = 1.0
                    else:
                        accepted = False
                        reward = 0.0
            else:
                accepted = False
                reward = 0.0

            if accepted:
                current_solution = candidate.copy()
                accepted_candidates_count += 1
            else:
                rejected_candidates_count += 1

            # Update Adaptive Operator Weights
            rf = 0.2
            destroy_weights[sel_destroy] = max(
                0.1, (1.0 - rf) * destroy_weights[sel_destroy] + rf * reward
            )
            repair_weights[sel_repair] = max(
                0.1, (1.0 - rf) * repair_weights[sel_repair] + rf * reward
            )

            # Cool temperature
            T = max(T_min, T * cooling_rate)


        # Step 11: Top solutions handling (distinct solutions ranked by objective_value)
        distinct_solutions: list[ALNSSolution] = []
        seen_signatures: set[tuple] = set()

        feasible_solutions.sort(
            key=lambda s: s.objective_value if s.objective_value is not None else float("inf")
        )

        for sol in feasible_solutions:
            signature = tuple(
                (rec.timetable_record_id, rec.resource_id)
                for rec in sorted(
                    sol.records.values(), key=lambda r: r.timetable_record_id
                )
                if rec.timetable_record_id in {r.timetable_record_id for r in affected_records}
            )

            if signature not in seen_signatures:
                seen_signatures.add(signature)
                distinct_solutions.append(sol)

        top_solutions = distinct_solutions[:3]

        if top_solutions:
            best_solution = top_solutions[0]
            best_objective = best_solution.objective_value
            best_total_delay = best_solution.total_delay_minutes
            best_passenger_impact = best_solution.passenger_impact_minutes
        elif best_solution:
            best_objective = best_solution.objective_value
            best_total_delay = best_solution.total_delay_minutes
            best_passenger_impact = best_solution.passenger_impact_minutes
        else:
            best_objective = None
            best_total_delay = None
            best_passenger_impact = None

        elapsed = time.time() - start_time

        return ALNSOptimizationResult(
            disruption=disruption,
            affected_records=affected_records,
            iterations=actual_iterations_executed,
            candidates_generated_count=candidates_generated_count,
            feasible_candidates_count=len(feasible_solutions),
            best_solution=best_solution,
            best_objective=best_objective,
            best_total_delay=best_total_delay,
            best_passenger_impact=best_passenger_impact,
            top_solutions=top_solutions,
            repairs_generated=repairs,
            execution_time_seconds=elapsed,
            destroy_operator_usage=destroy_usage,
            repair_operator_usage=repair_usage,
            destroy_operator_weights=destroy_weights,
            repair_operator_weights=repair_weights,
            accepted_candidates_count=accepted_candidates_count,
            rejected_candidates_count=rejected_candidates_count,
        )



if __name__ == "__main__":
    disruption = Disruption(
        disruption_type="PLATFORM_CLOSURE",
        station_code="MS",
        resource_id="MS-P9",
        start_time="05:00:00",
        end_time="05:20:00",
        day=1,
    )

    optimizer = ALNSOptimizer()
    result = optimizer.optimize(disruption, iterations=10)

    print("ALNS Optimizer Test")
    print("-------------------")
    for key, value in result.get_summary().items():
        print(f"  {key:<30}: {value}")

    if result.best_solution:
        print("\nBest Solution Affected Records Reassignment:")
            
        for rec_id in [r.timetable_record_id for r in result.affected_records]:
            rec = result.best_solution.get_record(rec_id)
            print(
                    f"  Train {rec.train_number} @ {rec.station_code} (Stop {rec.stop_number}): "
                    f"Original {rec.original_resource_id} -> Reassigned {rec.resource_id} "
                    f"(Platform {rec.platform_number})"
                )

    print("\nTop 3 Recovery Solutions:")
    print("-------------------------")

    affected_ids = [r.timetable_record_id for r in result.affected_records]

    for index, solution in enumerate(result.top_solutions, start=1):
        print(f"\nSolution {index}:")
        print(f"  Objective       : {solution.objective_value}")
        print(f"  Total Delay     : {solution.total_delay_minutes}")
        print(f"  Passenger Impact: {solution.passenger_impact_minutes}")
        print(f"  Feasible        : {solution.is_feasible}")

        for rec_id in affected_ids:
            rec = solution.get_record(rec_id)
            print(
                    f"  Train {rec.train_number} @ {rec.station_code} "
                    f"(Stop {rec.stop_number}): "
                    f"{rec.original_resource_id} -> {rec.resource_id} "
                    f"(Platform {rec.platform_number})"
                    )
