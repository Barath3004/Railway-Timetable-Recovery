from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TimetableRecord:
    """One timetable stop used by the ALNS optimizer."""

    timetable_record_id: int
    train_number: str
    station_code: str
    day: int
    stop_number: int

    arrival: str | None
    departure: str | None

    resource_id: str | None
    platform_number: int | None
    platform_type: str | None

    original_arrival: str | None = None
    original_departure: str | None = None
    original_resource_id: str | None = None
    original_platform_number: int | None = None

    def __post_init__(self) -> None:
        """Store original values when the record is first created."""

        if self.original_arrival is None:
            self.original_arrival = self.arrival

        if self.original_departure is None:
            self.original_departure = self.departure

        if self.original_resource_id is None:
            self.original_resource_id = self.resource_id

        if self.original_platform_number is None:
            self.original_platform_number = self.platform_number


@dataclass
class ALNSSolution:
    """
    Candidate timetable maintained by the ALNS optimizer.

    The SQLite database remains unchanged. ALNS works on copies
    of timetable records stored in memory.
    """

    records: dict[int, TimetableRecord] = field(default_factory=dict)

    objective_value: float | None = None
    total_delay_minutes: float = 0.0
    passenger_impact_minutes: float = 0.0

    is_feasible: bool = False

    def copy(self) -> "ALNSSolution":
        """Return a completely independent copy of the solution."""
        return deepcopy(self)

    def get_record(self, timetable_record_id: int) -> TimetableRecord:
        """Return one timetable record by its ID."""
        return self.records[timetable_record_id]

    def add_record(self, record: TimetableRecord) -> None:
        """Add or replace a timetable record."""
        self.records[record.timetable_record_id] = record

    def remove_record(self, timetable_record_id: int) -> None:
        """Remove a timetable record."""
        self.records.pop(timetable_record_id, None)

    def record_count(self) -> int:
        """Return the number of timetable records."""
        return len(self.records)

    def get_train_records(self, train_number: str) -> list[TimetableRecord]:
        """Return records for one train ordered by stop number."""
        records = [
            record
            for record in self.records.values()
            if record.train_number == train_number
        ]

        return sorted(records, key=lambda record: record.stop_number)

    def reset_evaluation(self) -> None:
        """Reset objective/evaluation values before reevaluation."""
        self.objective_value = None
        self.total_delay_minutes = 0.0
        self.passenger_impact_minutes = 0.0
        self.is_feasible = False