# ALNS Orchestration Implementation Report

## 1. Date
September 24, 2026

## 2. Task
The task was to connect/orchestrate all existing, verified individual ALNS components (`ALNSDataLoader`, `DisruptionFilter`, `ALNSDestroyOperator`, `ALNSRepairOperator`, `CandidateBuilder`, `FeasibilityChecker`, `CandidateEvaluator`) into a complete ALNS optimization workflow in `src/optimization/alns_optimizer.py` without modifying the existing architecture, database tables, ML models, or core operators.

## 3. Files Inspected
The following existing codebase files were inspected to understand their APIs and data contracts:
* `src/optimization/alns_solution.py`
* `src/optimization/alns_data_loader.py`
* `src/optimization/alns_disruption.py`
* `src/optimization/alns_destroy.py`
* `src/optimization/alns_move.py`
* `src/optimization/alns_candidate.py`
* `src/optimization/alns_allocation.py`
* `src/optimization/alns_feasibility.py`
* `src/optimization/alns_repair.py`
* `src/optimization/alns_evaluation.py`
* `analysis/passenger/manual_alns_ml_test.py`

## 4. Files Created
* [alns_optimizer.py](file:///C:/Users/barat/Desktop/Railway-Timetable-Recovery/src/optimization/alns_optimizer.py): Main orchestration layer module containing `ALNSOptimizer` and `ALNSOptimizationResult`.
* [test_alns_optimizer.py](file:///C:/Users/barat/Desktop/Railway-Timetable-Recovery/analysis/optimization/test_alns_optimizer.py): Dedicated unit test suite executing all 10 required orchestration tests.
* [ALNS_ORCHESTRATION_IMPLEMENTATION_REPORT.md](file:///C:/Users/barat/Desktop/Railway-Timetable-Recovery/docs/ALNS_ORCHESTRATION_IMPLEMENTATION_REPORT.md): Mandatory factual completion report.

## 5. Files Modified
* **None**: Zero existing files were modified. All existing modules were preserved as the source of truth and integrated cleanly via object composition.

## 6. Existing Components Reused
* **Data Loader**: `load_initial_solution()` from `src.optimization.alns_data_loader` loads the baseline 2469 timetable records into memory.
* **Disruption Filter**: `DisruptionFilter` from `src.optimization.alns_disruption` queries SQLite resource allocations to identify affected timetable records overlapping the disruption window.
* **Destroy Operator**: `ALNSDestroyOperator` from `src.optimization.alns_destroy` clears platform assignments for affected records on in-memory solution copies.
* **Repair Operator**: `ALNSRepairOperator` from `src.optimization.alns_repair` finds compatible alternative platforms at the station respecting train type rules (EMU/MEMU vs Mainline).
* **Candidate Builder**: `CandidateBuilder.apply_modification()` from `src.optimization.alns_candidate` applies `TimetableModification` objects to produce candidate solutions.
* **Feasibility Checker**: `FeasibilityChecker` from `src.optimization.alns_feasibility` checks candidate platform existence and conflict-free occupancy intervals including recovery buffers.
* **Candidate Evaluator**: `CandidateEvaluator` from `src.optimization.alns_evaluation` estimates positive train delay and passenger impact using `HistGradientBoostingRegressor` (`passenger_impact_model.joblib`) to calculate normalized objective values.

## 7. Orchestration Workflow
The implemented workflow proceeds as follows:
1. `load_initial_solution(db_path)` loads the timetable into `initial_solution`.
2. `DisruptionFilter.find_affected_records(disruption, initial_solution)` identifies affected timetable records.
3. `ALNSDestroyOperator.destroy_records(initial_solution, affected_records)` clears resource assignments on an in-memory copy (`destroyed_solution`).
4. `ALNSRepairOperator.generate_repairs(initial_solution, affected_records, disruption)` generates feasible `RepairCandidate` objects for affected records.
5. Complete candidate solutions are constructed by taking the Cartesian product of compatible repairs across all affected records.
6. Each complete candidate is evaluated via `CandidateEvaluator.evaluate(candidate)`.
7. Infeasible candidates receive `objective_value = inf` and `is_feasible = False` and are rejected.
8. Feasible candidates are sorted by `objective_value` ascending.
9. Up to 3 distinct feasible recovery alternatives are extracted and returned alongside execution statistics.

## 8. Multi-Record Candidate Generation
Individual repairs generated for each affected record are grouped by `timetable_record_id`. Complete candidate solutions are constructed using `itertools.product(*repair_lists)` to guarantee every affected record in the candidate is assigned a valid alternative platform. Each combination is sequentially applied to an in-memory copy of `initial_solution` via `CandidateBuilder.apply_modification()`. To prevent uncontrolled combinatorial explosion, candidate generation is bounded by `max_candidates` (default: 500).

## 9. ALNS Iteration Logic
The optimizer iterates across the configured number of iterations (e.g. 10 iterations). In each iteration, complete candidate combinations are constructed, evaluated, and checked for feasibility. The optimizer maintains the overall `best_solution` (lowest objective value) and updates `best_objective`, `best_total_delay`, and `best_passenger_impact`.

## 10. Adaptive Behavior
> [!NOTE]
> **NO ADAPTIVE OPERATOR WEIGHTING IMPLEMENTED (EXPLICIT STATEMENT)**:
> The existing project codebase contains exactly 1 Destroy operator (`ALNSDestroyOperator`) and 1 Repair operator (`ALNSRepairOperator`). Because no multiple alternative destroy or repair operators exist in the architecture, roulette-wheel adaptive operator selection or dynamic operator weight adjustment was NOT implemented, as doing so would introduce unrequested design assumptions.

## 11. Top-3 Solution Handling
Feasible candidates are sorted by `objective_value` ascending. Distinct solutions are filtered by computing a unique signature `tuple((timetable_record_id, resource_id))` across affected records. Up to 3 top distinct feasible solutions are returned in `result.top_solutions`, ensuring railway operators receive distinct, high-quality recovery choices.

## 12. Tests Executed
1. `python -m src.optimization.alns_optimizer`
2. `python analysis/optimization/test_alns_optimizer.py`

## 13. Test Results
* **Total Tests Executed**: 10
* **Tests Passed**: 10 (100% PASS)
* **Disruption Scenario Tested**: `PLATFORM_CLOSURE` at station `MS`, resource `MS-P9`, time `05:00:00 -> 05:20:00`, Day 1.
* **Affected Records**: 2 records (Train 40503 and Train 40505).
* **Candidates Generated**: 100
* **Feasible Candidates**: 100
* **Best Objective**: 0.0000
* **Best Total Delay**: 0.0 minutes
* **Best Passenger Impact**: 0.0 minutes
* **Top Distinct Solutions Returned**: 3
* **Execution Time**: ~37.6s for optimizer run, ~106.1s for full test suite.

## 14. Existing Files Not Modified
* `src/optimization/alns_solution.py`
* `src/optimization/alns_data_loader.py`
* `src/optimization/alns_disruption.py`
* `src/optimization/alns_destroy.py`
* `src/optimization/alns_move.py`
* `src/optimization/alns_candidate.py`
* `src/optimization/alns_allocation.py`
* `src/optimization/alns_feasibility.py`
* `src/optimization/alns_repair.py`
* `src/optimization/alns_evaluation.py`
* `data/database/railway_recovery.db`
* `data/processed/passenger_ml/final_model/passenger_impact_model.joblib`

## 15. Problems Encountered
* Direct script execution (`python src/optimization/alns_optimizer.py`) threw `ModuleNotFoundError: No module named 'src'`. Resolved by running scripts via module invocation (`python -m src.optimization.alns_optimizer`) or appending `PROJECT_ROOT` to `sys.path`.

## 16. Decisions Made
1. **Cartesian Product Candidate Combination [REQUIRES USER REVIEW]**: Used `itertools.product` bounded by `max_candidates=500` to construct complete multi-record candidates safely without uncontrolled memory usage.
2. **Distinct Solution Signature Deduplication [REQUIRES USER REVIEW]**: Deduplicated top solutions based on affected records' resource assignment tuples `(timetable_record_id, resource_id)`.
3. **Preservation of Single Operator Setup [REQUIRES USER REVIEW]**: Maintained single destroy and repair operator orchestration without inventing extra fake operators.

## 17. Remaining Work
* Integration of the ALNS orchestration layer with the web/UI dashboard layer for interactive disruption scenario simulation.

## 18. Exact Commands to Reproduce
Run the following PowerShell commands from the project root (`C:\Users\barat\Desktop\Railway-Timetable-Recovery`):

```powershell
# Run the ALNS Orchestration Layer self-test module
python -m src.optimization.alns_optimizer

# Run the full ALNS Orchestration unit test suite (10 tests)
python analysis/optimization/test_alns_optimizer.py
```
