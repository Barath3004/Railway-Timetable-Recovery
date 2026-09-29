# ALNS Feasibility and Orchestration Correction Report

## 1. Exact Files Inspected
* `src/optimization/alns_allocation.py`
* `src/optimization/alns_feasibility.py`
* `src/optimization/alns_optimizer.py`
* `src/optimization/alns_solution.py`
* `src/optimization/alns_repair.py`
* `src/optimization/alns_candidate.py`
* `src/optimization/alns_evaluation.py`
* `analysis/optimization/test_alns_optimizer.py`

## 2. Exact Files Modified or Created
* **Modified**: `src/optimization/alns_feasibility.py`
* **Modified**: `src/optimization/alns_optimizer.py`
* **Modified**: `analysis/optimization/test_alns_optimizer.py`
* **Created**: `analysis/optimization/test_candidate_feasibility_regression.py`
* **Created**: `docs/ALNS_CORRECTION_REPORT.md`

## 3. Defects Identified and Corrections Applied

### Feasibility Defects
1. **Candidate-Unaware Conflict Detection**:
   * *Defect*: `check_platform_conflict` previously queried SQLite baseline allocations only and failed to compare modified records in `ALNSSolution` against each other.
   * *Correction*: Updated `check_platform_conflict` to check candidate allocations against both unchanged SQLite baseline allocations and proposed candidate allocations of other modified records in `solution`.
2. **Obsolete Baseline Allocation Inclusion**:
   * *Defect*: When a train was reassigned to a new platform or time slot, its original SQLite baseline allocation remained active in conflict checking, causing false conflict rejections.
   * *Correction*: Excluded SQLite baseline rows matching any `timetable_record_id` that is modified in `solution`.
3. **Candidate Timing for Departure-Only Records**:
   * *Defect*: `get_candidate_allocation` used `original_allocation.allocation_start` for departure-only records (`arrival is None`) even when `record.departure` was modified in candidate.
   * *Correction*: Updated `get_candidate_allocation` to compute `start_time = candidate_departure - occupancy_minutes` for departure-only records.
4. **Cross-Midnight and Day Context Handling**:
   * *Defect*: `_intervals_overlap` compared clock times without full weekly day offset context.
   * *Correction*: Implemented `_allocation_to_weekly_intervals` mapping day (1-7) and time intervals into a 10080-minute weekly interval space `[start, end)`, accurately handling same-day overlaps, cross-midnight allocations, adjacent-day overlaps, touching release times, and 7-day wrap-around.
5. **Unrepaired Affected Record Checking**:
   * *Defect*: Pre-existing baseline records with `resource_id is None` caused false solution rejections while destroyed affected records left unrepaired were not specifically flagged.
   * *Correction*: Updated `check_solution` to flag any affected record where `original_resource_id is not None` but candidate `resource_id is None` as an unrepaired violation, while preserving unchanged baseline records.

### Orchestration Defects
6. **Unused Destroyed Solution**:
   * *Defect*: Candidate building constructed candidate copies from `initial_solution` instead of starting from `destroyed_solution`.
   * *Correction*: Updated `ALNSOptimizer.optimize` to initialize candidates from `destroyed_solution.copy()`.
7. **Incomplete Repairs**:
   * *Defect*: If an affected record had no available repairs, the optimizer attempted to return an incomplete candidate.
   * *Correction*: Verified `len(records_with_repairs) == len(affected_records)`. If any affected record lacks a repair, `best_solution = None` and `top_solutions = []` are returned.
8. **Unbounded Cartesian Product**:
   * *Defect*: Materialized all repair combinations into a python list before slicing, risking memory exhaustion.
   * *Correction*: Used `itertools.islice(itertools.product(*repair_lists), max_candidates)` for lazy candidate combination generation.
9. **Iteration Count Reporting**:
   * *Defect*: Reported requested iterations instead of actual iterations executed.
   * *Correction*: Set `iterations = actual_iterations_executed`.

## 4. How Complete-Candidate Conflicts Are Checked
`check_platform_conflict(record, candidate_allocation, solution)` validates a candidate allocation against:
1. Unchanged baseline SQLite allocations for records that are NOT modified in `solution`.
2. Proposed allocations of all other modified records in `solution` assigned to the same station resource.
Interval overlaps are evaluated using `_intervals_overlap()` on weekly minute intervals `[start, release)`.

## 5. How Obsolete Baseline Allocations Are Excluded
`modified_record_ids` collects `timetable_record_id` for all records modified in `solution`. When querying SQLite `resource_allocations`, any baseline row matching `modified_record_ids` is explicitly skipped (`if db_rec_id in modified_record_ids: continue`).

## 6. How Departure-Only and Cross-Midnight Timing Are Handled
* **Departure-Only**: `start_time = candidate_departure - occupancy_minutes`.
* **Cross-Midnight**: `_allocation_to_weekly_intervals` converts `(day 1..7, start_time, release_time)` into absolute weekly minute intervals `[abs_start, abs_end)`. If `release_time < start_time`, `abs_end += 1440`. If `abs_end > 10080`, it wraps to `[(abs_start, 10080), (0, abs_end - 10080)]`.

## 7. How Incomplete Repairs Are Rejected
* If any affected record has no generated repair candidates (`len(records_with_repairs) < len(affected_records)`), `ALNSOptimizer` immediately returns `best_solution = None`.
* `FeasibilityChecker.check_solution()` flags any record with `original_resource_id is not None` and `resource_id is None` as an unrepaired violation.

## 8. How Candidate Generation Is Bounded
`bounded_combinations = list(itertools.islice(itertools.product(*repair_lists), max_candidates))` lazily generates up to `max_candidates` complete combinations without materializing larger combinatorial spaces into memory.

## 9. Actual Iteration Behavior
`ALNSOptimizer.optimize` loops through requested `iterations`, constructing and evaluating bounded complete candidates per pass, updating `actual_iterations_executed` and returning accurate iteration counts.

## 10. Tests Executed, Exact Commands, and Results

### Command 1: Feasibility Regression Test Suite
```powershell
python analysis/optimization/test_candidate_feasibility_regression.py
```
* **Result**: `Ran 6 tests in 0.341s - OK`
* **Output**:
  - `PASS 1`: Two modified records overlapping on the same platform flagged as INFEASIBLE.
  - `PASS 2`: Two modified records non-overlapping on the same platform are FEASIBLE.
  - `PASS 3`: Obsolete baseline allocation of modified train successfully EXCLUDED.
  - `PASS 4`: Candidate timing for departure-only record correctly calculated.
  - `PASS 5`: Midnight crossing and day handling verified across all test cases.
  - `PASS 6`: Affected record with resource_id = None rejected as INFEASIBLE.

### Command 2: Extended Orchestration Test Suite
```powershell
python analysis/optimization/test_alns_optimizer.py
```
* **Result**: `Ran 15 tests in 61.495s - OK`
* **Output Summary for MS-P9 Disruption (`05:00:00 -> 05:20:00`, Day 1)**:
  - `disruption_type`: PLATFORM_CLOSURE
  - `station_code`: MS
  - `resource_id`: MS-P9
  - `affected_record_count`: 2 (Train 40503 & Train 40505)
  - `candidates_generated`: 100
  - `feasible_candidates`: 100
  - `best_objective`: 0.0000
  - `best_total_delay_minutes`: 0.0
  - `best_passenger_impact_minutes`: 0.0
  - `top_solutions_count`: 3 (Reassignments: MS-P1, MS-P2, MS-P3)
  - `PASS 1 - PASS 15`: All 15 unit tests passed cleanly.

## 11. Failing Tests or Unresolved Limitations
* **Failing Tests**: None (0 failures).
* **Limitations**: Current setup utilizes 1 Destroy operator and 1 Repair operator; roulette-wheel adaptive operator weighting is intentionally not implemented to avoid unrequested design assumptions.

## 12. Design Assumptions Requiring User Approval
> [!NOTE]
> 1. **Lazy Combination Bounding**: Used `itertools.islice` with `max_candidates=500` to prevent memory exhaustion during Cartesian product generation across multi-record disruptions.
> 2. **Distinct Solution Signature**: Deduplicated Top-3 feasible solutions using solution signatures `tuple((timetable_record_id, resource_id))` across affected records.
> 3. **Single Operator Preservation**: Retained single destroy and repair operator structure without introducing fake operators.

## 13. Remaining Work Before Implementing Adaptive ALNS
* Implement additional destroy and repair operators (e.g. random destroy, worst delay destroy, buffer adjustment repair) if dynamic roulette-wheel operator selection is desired.
* Integrate optimizer with Web UI / Dashboard API.
