from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TimetableModification:
    """
    Represents one proposed change to a timetable record.

    This does not modify the database directly.
    It describes what ALNS wants to change in a candidate solution.
    """

    timetable_record_id: int

    new_arrival: str | None = None
    new_departure: str | None = None

    new_resource_id: str | None = None
    new_platform_number: int | None = None
    new_platform_type: str | None = None

    reason: str = ""

    def has_timing_change(self) -> bool:
        """Return True if the modification changes arrival or departure."""

        return (
            self.new_arrival is not None
            or self.new_departure is not None
        )

    def has_resource_change(self) -> bool:
        """Return True if the modification changes the resource/platform."""

        return (
            self.new_resource_id is not None
            or self.new_platform_number is not None
            or self.new_platform_type is not None
        )


if __name__ == "__main__":
    modification = TimetableModification(
        timetable_record_id=9033,
        new_resource_id="MAS-P5",
        new_platform_number=5,
        new_platform_type="MAINLINE",
        reason="Platform MAS-P4 unavailable due to disruption",
    )

    print("ALNS timetable modification test")
    print("---------------------------------")

    print(f"Timetable record : {modification.timetable_record_id}")
    print(f"New resource     : {modification.new_resource_id}")
    print(f"New platform     : {modification.new_platform_number}")
    print(f"New platform type: {modification.new_platform_type}")
    print(f"Reason           : {modification.reason}")

    print(f"\nTiming change   : {modification.has_timing_change()}")
    print(f"Resource change : {modification.has_resource_change()}")