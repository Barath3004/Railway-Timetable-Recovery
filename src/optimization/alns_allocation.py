from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


TIME_FORMAT = "%H:%M:%S"
MIN_RECOVERY_BUFFER_MINUTES = 5


@dataclass
class CandidateAllocation:
    """Represents the resource occupancy of an ALNS candidate."""

    timetable_record_id: int
    resource_id: str
    day: int
    allocation_start: str
    allocation_end: str
    buffer_minutes: int
    release_time: str
    occupancy_minutes: int


class CandidateAllocationCalculator:
    """
    Calculate the resource allocation interval for an ALNS candidate.

    The calculation happens only in memory.
    The SQLite database is never modified.

    For a timetable record:
        allocation_start -> allocation_end
        represents the train's actual platform occupancy.

    The resource remains reserved until:
        allocation_end + buffer

    For a zero-dwell record:
        allocation_start == allocation_end

    In that case, the buffer represents resource clearance,
    not train dwell time.
    """

    @staticmethod
    def _parse_time(time_value: str) -> datetime:
        return datetime.strptime(time_value, TIME_FORMAT)

    @staticmethod
    def _format_time(time_value: datetime) -> str:
        return time_value.strftime(TIME_FORMAT)

    @staticmethod
    def validate_buffer(buffer_minutes: int) -> None:
        """Ensure the recovery buffer respects the project minimum."""
        if buffer_minutes < MIN_RECOVERY_BUFFER_MINUTES:
            raise ValueError(
                f"Recovery buffer cannot be less than "
                f"{MIN_RECOVERY_BUFFER_MINUTES} minutes."
            )

    def calculate(
        self,
        timetable_record_id: int,
        resource_id: str,
        day: int,
        arrival: str,
        departure: str,
        buffer_minutes: int,
    ) -> CandidateAllocation:
        """
        Calculate an allocation from timetable arrival/departure.

        For zero dwell:
            arrival == departure

        This is valid. It means the train has zero scheduled dwell,
        while the buffer controls resource clearance.
        """
        if not resource_id:
            raise ValueError("resource_id cannot be empty.")

        if day < 1:
            raise ValueError("day must be greater than or equal to 1.")

        if not arrival:
            raise ValueError("arrival cannot be empty.")

        if not departure:
            raise ValueError("departure cannot be empty.")

        self.validate_buffer(buffer_minutes)

        arrival_time = self._parse_time(arrival)
        departure_time = self._parse_time(departure)

        if departure_time < arrival_time:
            departure_time += timedelta(days=1)

        occupancy_minutes = int(
            (departure_time - arrival_time).total_seconds() / 60
        )

        release_time = departure_time + timedelta(
            minutes=buffer_minutes
        )

        return CandidateAllocation(
            timetable_record_id=timetable_record_id,
            resource_id=resource_id,
            day=day,
            allocation_start=self._format_time(arrival_time),
            allocation_end=self._format_time(departure_time),
            buffer_minutes=buffer_minutes,
            release_time=self._format_time(release_time),
            occupancy_minutes=occupancy_minutes,
        )

    def calculate_from_allocation_start(
        self,
        timetable_record_id: int,
        resource_id: str,
        day: int,
        allocation_start: str,
        occupancy_minutes: int,
        buffer_minutes: int,
    ) -> CandidateAllocation:
        """
        Calculate an allocation when the database already provides
        the resource allocation start and occupancy duration.

        This is important for origin/departure-only records where
        timetable arrival is NULL.

        Example:

            allocation_start = 15:15
            occupancy       = 0
            buffer           = 25

        produces:

            15:15 -> 15:15
            release = 15:40

        The 25 minutes are resource clearance, not train dwell.
        """
        if not resource_id:
            raise ValueError("resource_id cannot be empty.")

        if day < 1:
            raise ValueError("day must be greater than or equal to 1.")

        if occupancy_minutes < 0:
            raise ValueError("occupancy_minutes cannot be negative.")

        self.validate_buffer(buffer_minutes)

        start_time = self._parse_time(allocation_start)

        end_time = start_time + timedelta(
            minutes=occupancy_minutes
        )

        release_time = end_time + timedelta(
            minutes=buffer_minutes
        )

        return CandidateAllocation(
            timetable_record_id=timetable_record_id,
            resource_id=resource_id,
            day=day,
            allocation_start=self._format_time(start_time),
            allocation_end=self._format_time(end_time),
            buffer_minutes=buffer_minutes,
            release_time=self._format_time(release_time),
            occupancy_minutes=occupancy_minutes,
        )


if __name__ == "__main__":
    calculator = CandidateAllocationCalculator()

    print("ALNS candidate allocation test")
    print("------------------------------")

    # Zero-dwell example
    zero_dwell = calculator.calculate(
        timetable_record_id=9033,
        resource_id="MAS-P5",
        day=1,
        arrival="15:15:00",
        departure="15:15:00",
        buffer_minutes=25,
    )

    print("\nZero-dwell candidate:")
    print(f"Resource         : {zero_dwell.resource_id}")
    print(f"Allocation start : {zero_dwell.allocation_start}")
    print(f"Allocation end   : {zero_dwell.allocation_end}")
    print(f"Occupancy        : {zero_dwell.occupancy_minutes} minutes")
    print(f"Buffer           : {zero_dwell.buffer_minutes} minutes")
    print(f"Release time     : {zero_dwell.release_time}")

    # Minimum recovery buffer example
    minimum_buffer = calculator.calculate(
        timetable_record_id=9033,
        resource_id="MAS-P5",
        day=1,
        arrival="15:15:00",
        departure="15:15:00",
        buffer_minutes=MIN_RECOVERY_BUFFER_MINUTES,
    )

    print("\nMinimum recovery-buffer candidate:")
    print(f"Resource         : {minimum_buffer.resource_id}")
    print(f"Allocation start : {minimum_buffer.allocation_start}")
    print(f"Allocation end   : {minimum_buffer.allocation_end}")
    print(f"Occupancy        : {minimum_buffer.occupancy_minutes} minutes")
    print(f"Buffer           : {minimum_buffer.buffer_minutes} minutes")
    print(f"Release time     : {minimum_buffer.release_time}")