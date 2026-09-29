from __future__ import annotations

from src.optimization.alns_move import TimetableModification
from src.optimization.alns_solution import ALNSSolution


class CandidateBuilder:
    """Create candidate ALNS solutions from timetable modifications."""

    @staticmethod
    def apply_modification(
        solution: ALNSSolution,
        modification: TimetableModification,
    ) -> ALNSSolution:
        """
        Create a new candidate solution and apply one modification.

        The original solution is never changed.
        """

        if modification.timetable_record_id not in solution.records:
            raise KeyError(
                f"Timetable record not found: "
                f"{modification.timetable_record_id}"
            )

        candidate = solution.copy()

        record = candidate.records[modification.timetable_record_id]

        if modification.new_arrival is not None:
            record.arrival = modification.new_arrival

        if modification.new_departure is not None:
            record.departure = modification.new_departure

        if modification.new_resource_id is not None:
            record.resource_id = modification.new_resource_id

        if modification.new_platform_number is not None:
            record.platform_number = modification.new_platform_number

        if modification.new_platform_type is not None:
            record.platform_type = modification.new_platform_type

        candidate.reset_evaluation()

        return candidate


if __name__ == "__main__":
    from src.optimization.alns_data_loader import load_initial_solution

    solution = load_initial_solution()

    record_id = 9033

    original_record = solution.get_record(record_id)

    modification = TimetableModification(
        timetable_record_id=record_id,
        new_resource_id="MAS-P5",
        new_platform_number=5,
        new_platform_type="MAINLINE",
        reason="Platform MAS-P4 unavailable due to disruption",
    )

    candidate = CandidateBuilder.apply_modification(
        solution,
        modification,
    )

    original_after = solution.get_record(record_id)
    candidate_record = candidate.get_record(record_id)

    print("ALNS candidate generation test")
    print("-----------------------------")

    print("Original solution:")
    print(f"  Resource : {original_record.resource_id}")
    print(f"  Platform : {original_record.platform_number}")

    print("\nCandidate solution:")
    print(f"  Resource : {candidate_record.resource_id}")
    print(f"  Platform : {candidate_record.platform_number}")

    print("\nOriginal solution after modification:")
    print(f"  Resource : {original_after.resource_id}")
    print(f"  Platform : {original_after.platform_number}")

    original_unchanged = (
        original_after.resource_id == "MAS-P4"
        and original_after.platform_number == 4
    )

    candidate_changed = (
        candidate_record.resource_id == "MAS-P5"
        and candidate_record.platform_number == 5
    )

    print("\nValidation:")
    print(
        f"  Original unchanged : "
        f"{'PASS' if original_unchanged else 'FAIL'}"
    )
    print(
        f"  Candidate changed  : "
        f"{'PASS' if candidate_changed else 'FAIL'}"
    )