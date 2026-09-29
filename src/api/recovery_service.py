from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.optimization.alns_disruption import Disruption, DisruptionFilter
from src.optimization.alns_optimizer import ALNSOptimizationResult, ALNSOptimizer
from src.optimization.alns_data_loader import load_initial_solution


class RecoveryService:
    """Coordinates UI workflow state without changing ALNS or SQLite baseline data."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.optimizer = ALNSOptimizer(db_path=database_path)
        self._disruptions: dict[str, dict[str, Any]] = {}
        self._results: dict[str, ALNSOptimizationResult] = {}

    def detect_affected(self, payload: dict[str, Any]) -> dict[str, Any]:
        disruption = self._build_disruption(payload)
        initial_solution = load_initial_solution(self.database_path)
        affected = DisruptionFilter(self.database_path).find_affected_records(
            disruption, initial_solution
        )
        disruption_id = uuid4().hex
        data = {"id": disruption_id, **payload}
        self._disruptions[disruption_id] = data
        return {
            "disruption": data,
            "affected_records": [self._record_to_dict(record) for record in affected],
            "affected_train_count": len({record.train_number for record in affected}),
        }

    def optimize(self, disruption_id: str, iterations: int = 10) -> dict[str, Any]:
        payload = self._disruptions[disruption_id]
        result = self.optimizer.optimize(
            self._build_disruption(payload),
            iterations=max(1, min(iterations, 100)),
        )
        self._results[disruption_id] = result
        return self.result_to_dict(disruption_id, result)

    def result_to_dict(
        self, disruption_id: str, result: ALNSOptimizationResult
    ) -> dict[str, Any]:
        options = [
            self._solution_to_dict(solution, result.affected_records)
            for solution in result.top_solutions
        ]
        return {
            "recovery_id": disruption_id,
            "disruption": self._disruptions[disruption_id],
            "affected_records": [
                self._record_to_dict(record) for record in result.affected_records
            ],
            "metrics": {
                "iterations": result.iterations,
                "candidates_generated": result.candidates_generated_count,
                "feasible_candidates": result.feasible_candidates_count,
                "accepted_candidates": result.accepted_candidates_count,
                "rejected_candidates": result.rejected_candidates_count,
                "execution_time_seconds": round(result.execution_time_seconds, 3),
                "best_objective": result.best_objective,
                "total_delay_minutes": result.best_total_delay,
                "passenger_impact_minutes": result.best_passenger_impact,
            },
            "options": options,
        }

    def get_result(self, recovery_id: str) -> dict[str, Any]:
        result = self._results[recovery_id]
        return self.result_to_dict(recovery_id, result)

    def get_disruption(self, disruption_id: str) -> dict[str, Any]:
        return self._disruptions[disruption_id]

    @staticmethod
    def _build_disruption(payload: dict[str, Any]) -> Disruption:
        return Disruption(
            disruption_type=str(payload["disruption_type"]),
            station_code=str(payload["station_code"]),
            resource_id=str(payload["resource_id"]),
            start_time=str(payload["start_time"]),
            end_time=str(payload["end_time"]),
            day=int(payload["day"]),
        )

    @staticmethod
    def _record_to_dict(record: Any) -> dict[str, Any]:
        return {
            "timetable_record_id": record.timetable_record_id,
            "train_number": record.train_number,
            "station_code": record.station_code,
            "day": record.day,
            "stop_number": record.stop_number,
            "arrival": record.arrival,
            "departure": record.departure,
            "resource_id": record.resource_id,
            "platform_number": record.platform_number,
            "platform_type": record.platform_type,
            "original_resource_id": record.original_resource_id,
            "original_platform_number": record.original_platform_number,
            "status": "Affected",
        }

    def _solution_to_dict(self, solution: Any, affected: list[Any]) -> dict[str, Any]:
        changes = []
        affected_ids = {record.timetable_record_id for record in affected}
        for record in solution.records.values():
            if record.timetable_record_id not in affected_ids:
                continue
            if (
                record.resource_id != record.original_resource_id
                or record.platform_number != record.original_platform_number
                or record.arrival != record.original_arrival
                or record.departure != record.original_departure
            ):
                changes.append(self._record_to_dict(record))
        return {
            "objective": solution.objective_value,
            "total_delay_minutes": solution.total_delay_minutes,
            "passenger_impact_minutes": solution.passenger_impact_minutes,
            "feasible": solution.is_feasible,
            "changed_records": changes,
            "changed_count": len(changes),
        }
