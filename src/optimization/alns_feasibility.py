from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from src.optimization.alns_allocation import (
    CandidateAllocation,
    CandidateAllocationCalculator,
    MIN_RECOVERY_BUFFER_MINUTES,
)
from src.optimization.alns_solution import ALNSSolution, TimetableRecord


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "data" / "database" / "railway_recovery.db"


class FeasibilityChecker:
    """
    Check whether an ALNS candidate satisfies resource constraints.

    The checker never modifies SQLite.

    Resource conflicts are evaluated using:

        allocation_start -> release_time

    rather than only:

        allocation_start -> allocation_end

    This ensures that the recovery/clearance buffer is also
    respected.

    When an active disruption is supplied, the checker also
    verifies that a candidate does not use the disrupted
    resource during the disruption interval.
    """

    def __init__(
        self,
        database_path: Path = DATABASE_PATH,
        disruption=None,
    ) -> None:
        self.database_path = database_path
        self.disruption = disruption
        self.allocation_calculator = CandidateAllocationCalculator()

    def check_platform_exists(self, record: TimetableRecord) -> bool:
        """Check whether the candidate resource exists at the station."""
        if record.resource_id is None:
            return False

        connection = sqlite3.connect(self.database_path)

        try:
            row = connection.execute(
                """
                SELECT 1
                FROM platforms
                WHERE resource_id = ?
                  AND station_code = ?
                LIMIT 1
                """,
                (
                    record.resource_id,
                    record.station_code,
                ),
            ).fetchone()
        finally:
            connection.close()

        return row is not None

    def get_original_allocation(
        self,
        record: TimetableRecord,
    ) -> CandidateAllocation:
        """
        Retrieve the original resource allocation from SQLite.

        This provides the baseline resource interval for the
        candidate.

        The original database buffer is preserved as the normal
        buffer. ALNS may later test smaller recovery buffers,
        but never below the project minimum.
        """
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row

        try:
            row = connection.execute(
                """
                SELECT
                    allocation_start,
                    allocation_end,
                    occupancy_minutes,
                    buffer_minutes,
                    release_time
                FROM resource_allocations
                WHERE timetable_record_id = ?
                LIMIT 1
                """,
                (record.timetable_record_id,),
            ).fetchone()
        finally:
            connection.close()

        if row is None:
            raise ValueError(
                f"No resource allocation found for timetable "
                f"record {record.timetable_record_id}."
            )

        allocation_start = row["allocation_start"]
        occupancy_minutes = row["occupancy_minutes"]
        buffer_minutes = row["buffer_minutes"]

        if allocation_start is None:
            raise ValueError(
                f"Allocation start is missing for timetable "
                f"record {record.timetable_record_id}."
            )

        if occupancy_minutes is None:
            raise ValueError(
                f"Occupancy duration is missing for timetable "
                f"record {record.timetable_record_id}."
            )

        if buffer_minutes is None:
            raise ValueError(
                f"Buffer duration is missing for timetable "
                f"record {record.timetable_record_id}."
            )

        if buffer_minutes < MIN_RECOVERY_BUFFER_MINUTES:
            raise ValueError(
                f"Original buffer {buffer_minutes} minutes for "
                f"timetable record {record.timetable_record_id} "
                f"is below the ALNS minimum of "
                f"{MIN_RECOVERY_BUFFER_MINUTES} minutes."
            )

        return self.allocation_calculator.calculate_from_allocation_start(
            timetable_record_id=record.timetable_record_id,
            resource_id=record.resource_id or "",
            day=record.day,
            allocation_start=allocation_start,
            occupancy_minutes=occupancy_minutes,
            buffer_minutes=buffer_minutes,
        )

    def get_candidate_allocation(
        self,
        record: TimetableRecord,
        buffer_minutes: int | None = None,
    ) -> CandidateAllocation:
        """
        Calculate the candidate resource allocation.

        If buffer_minutes is not supplied, the original database
        buffer is used.
        """
        if record.resource_id is None:
            raise ValueError(
                f"Record {record.timetable_record_id} has no resource."
            )

        original_allocation = self.get_original_allocation(record)

        if buffer_minutes is None:
            buffer_minutes = original_allocation.buffer_minutes

        self.allocation_calculator.validate_buffer(
            buffer_minutes
        )

        # If both timetable times exist in candidate, use candidate arrival & departure.
        if (
            record.arrival is not None
            and record.departure is not None
        ):
            return self.allocation_calculator.calculate(
                timetable_record_id=record.timetable_record_id,
                resource_id=record.resource_id,
                day=record.day,
                arrival=record.arrival,
                departure=record.departure,
                buffer_minutes=buffer_minutes,
            )

        # Departure-only record.
        if record.arrival is None and record.departure is not None:
            dep_time = datetime.strptime(
                record.departure,
                "%H:%M:%S",
            )

            start_time = dep_time - timedelta(
                minutes=original_allocation.occupancy_minutes
            )

            if start_time.day < dep_time.day:
                start_time += timedelta(days=1)

            start_str = start_time.strftime("%H:%M:%S")

            return self.allocation_calculator.calculate_from_allocation_start(
                timetable_record_id=record.timetable_record_id,
                resource_id=record.resource_id,
                day=record.day,
                allocation_start=start_str,
                occupancy_minutes=original_allocation.occupancy_minutes,
                buffer_minutes=buffer_minutes,
            )

        # Arrival-only record.
        if record.arrival is not None and record.departure is None:
            return self.allocation_calculator.calculate_from_allocation_start(
                timetable_record_id=record.timetable_record_id,
                resource_id=record.resource_id,
                day=record.day,
                allocation_start=record.arrival,
                occupancy_minutes=original_allocation.occupancy_minutes,
                buffer_minutes=buffer_minutes,
            )

        # Fallback when both arrival and departure are None.
        return self.allocation_calculator.calculate_from_allocation_start(
            timetable_record_id=record.timetable_record_id,
            resource_id=record.resource_id,
            day=record.day,
            allocation_start=original_allocation.allocation_start,
            occupancy_minutes=original_allocation.occupancy_minutes,
            buffer_minutes=buffer_minutes,
        )

    @staticmethod
    def _time_to_minutes(time_value: str) -> int:
        """Convert HH:MM or HH:MM:SS to minutes from midnight."""
        if not time_value:
            return 0

        parts = time_value.split(":")

        return int(parts[0]) * 60 + int(parts[1])

    @classmethod
    def _allocation_to_weekly_intervals(
        cls,
        day: int,
        start_time: str,
        release_time: str,
    ) -> list[tuple[int, int]]:
        """
        Convert (day 1..7, start_time, release_time) into
        half-open minute intervals [start, end) within a
        10080-minute week.
        """
        start_min = cls._time_to_minutes(start_time)
        release_min = cls._time_to_minutes(release_time)

        day_offset = (
            max(1, min(7, int(day))) - 1
        ) * 1440

        abs_start = day_offset + start_min
        abs_end = day_offset + release_min

        if release_min < start_min:
            abs_end += 1440

        if abs_end <= 10080:
            return [(abs_start, abs_end)]

        return [
            (abs_start, 10080),
            (0, abs_end - 10080),
        ]

    @classmethod
    def _intervals_overlap(
        cls,
        day1: int,
        start1: str,
        release1: str,
        day2: int,
        start2: str,
        release2: str,
    ) -> bool:
        """Check whether two weekly resource allocations overlap."""
        intervals1 = cls._allocation_to_weekly_intervals(
            day1,
            start1,
            release1,
        )

        intervals2 = cls._allocation_to_weekly_intervals(
            day2,
            start2,
            release2,
        )

        for s1, e1 in intervals1:
            for s2, e2 in intervals2:
                if s1 < e2 and s2 < e1:
                    return True

        return False

    def check_disruption_conflict(
        self,
        record: TimetableRecord,
        candidate_allocation: CandidateAllocation,
    ) -> tuple[bool, list[str]]:
        """
        Check whether the candidate allocation overlaps the active
        disruption on the disrupted resource.

        The candidate is rejected only when:
        - an active disruption exists,
        - the candidate is at the same station,
        - the candidate uses the disrupted resource, and
        - the candidate allocation overlaps the disruption interval.

        Candidate release time is used so that clearance/buffer
        extending into the disruption window is also rejected.
        """
        if self.disruption is None:
            return False, []

        disruption_station = getattr(
            self.disruption,
            "station_code",
            None,
        )

        disruption_resource = getattr(
            self.disruption,
            "resource_id",
            None,
        )

        disruption_start = getattr(
            self.disruption,
            "start_time",
            None,
        )

        disruption_end = getattr(
            self.disruption,
            "end_time",
            None,
        )

        disruption_day = getattr(
            self.disruption,
            "day",
            None,
        )

        if (
            disruption_station is None
            or disruption_resource is None
            or disruption_start is None
            or disruption_end is None
            or disruption_day is None
        ):
            raise ValueError(
                "Active disruption must contain station_code, "
                "resource_id, start_time, end_time, and day."
            )

        if (
            record.station_code != disruption_station
            or candidate_allocation.resource_id != disruption_resource
        ):
            return False, []

        overlaps = self._intervals_overlap(
            candidate_allocation.day,
            candidate_allocation.allocation_start,
            candidate_allocation.release_time,
            int(disruption_day),
            str(disruption_start),
            str(disruption_end),
        )

        if not overlaps:
            return False, []

        disruption_type = getattr(
            self.disruption,
            "disruption_type",
            "RESOURCE_DISRUPTION",
        )

        return True, [
            f"Candidate resource {candidate_allocation.resource_id} "
            f"overlaps active {disruption_type} at "
            f"{record.station_code} "
            f"(Day {disruption_day} "
            f"{disruption_start} -> {disruption_end})."
        ]

    def check_platform_conflict(
        self,
        record: TimetableRecord,
        candidate_allocation: CandidateAllocation,
        solution: ALNSSolution | None = None,
    ) -> tuple[bool, list[str]]:
        """
        Check candidate allocation for conflicts against:

        1. Unchanged baseline SQLite allocations, excluding obsolete
           allocations of modified records.
        2. Proposed candidate allocations of other modified records
           in solution.
        """
        conflicts: list[str] = []

        modified_record_ids: set[int] = set()

        if solution is not None:
            for rec in solution.records.values():
                if (
                    rec.arrival != rec.original_arrival
                    or rec.departure != rec.original_departure
                    or rec.resource_id != rec.original_resource_id
                    or rec.platform_number != rec.original_platform_number
                ):
                    modified_record_ids.add(
                        rec.timetable_record_id
                    )

        # 1. Query baseline allocations from SQLite.
        connection = sqlite3.connect(
            self.database_path
        )

        connection.row_factory = sqlite3.Row

        try:
            rows = connection.execute(
                """
                SELECT
                    timetable_record_id,
                    station_code,
                    resource_id,
                    day,
                    allocation_start,
                    allocation_end,
                    release_time
                FROM resource_allocations
                WHERE station_code = ?
                  AND resource_id = ?
                  AND timetable_record_id != ?
                """,
                (
                    record.station_code,
                    candidate_allocation.resource_id,
                    candidate_allocation.timetable_record_id,
                ),
            ).fetchall()

        finally:
            connection.close()

        for row in rows:
            db_rec_id = row["timetable_record_id"]

            if db_rec_id in modified_record_ids:
                continue

            db_start = row["allocation_start"]
            db_release = (
                row["release_time"]
                or row["allocation_end"]
            )
            db_day = row["day"]

            if db_start is None or db_release is None:
                continue

            if self._intervals_overlap(
                candidate_allocation.day,
                candidate_allocation.allocation_start,
                candidate_allocation.release_time,
                db_day,
                db_start,
                db_release,
            ):
                conflicts.append(
                    f"Conflict with baseline timetable record "
                    f"{db_rec_id} on "
                    f"{candidate_allocation.resource_id} "
                    f"(Day {db_day} {db_start} -> {db_release})"
                )

        # 2. Check proposed candidate allocations of other modified
        # records in the solution.
        if solution is not None:
            for other_rec in solution.records.values():
                if (
                    other_rec.timetable_record_id
                    == record.timetable_record_id
                ):
                    continue

                if (
                    other_rec.timetable_record_id
                    not in modified_record_ids
                ):
                    continue

                if (
                    other_rec.resource_id
                    == candidate_allocation.resource_id
                    and other_rec.station_code
                    == record.station_code
                ):
                    try:
                        other_alloc = (
                            self.get_candidate_allocation(
                                other_rec
                            )
                        )
                    except ValueError:
                        continue

                    if self._intervals_overlap(
                        candidate_allocation.day,
                        candidate_allocation.allocation_start,
                        candidate_allocation.release_time,
                        other_alloc.day,
                        other_alloc.allocation_start,
                        other_alloc.release_time,
                    ):
                        conflicts.append(
                            f"Conflict with modified candidate "
                            f"train {other_rec.train_number} "
                            f"(record "
                            f"{other_rec.timetable_record_id}) "
                            f"on "
                            f"{candidate_allocation.resource_id} "
                            f"(Day {other_alloc.day} "
                            f"{other_alloc.allocation_start} "
                            f"-> {other_alloc.release_time})"
                        )

        return len(conflicts) > 0, conflicts

    def check_record(
        self,
        record: TimetableRecord,
        solution: ALNSSolution,
        buffer_minutes: int | None = None,
    ) -> tuple[bool, list[str]]:
        """
        Check one candidate record for:

        1. Resource existence.
        2. Active disruption overlap.
        3. Resource conflicts.
        """
        violations: list[str] = []

        if record.resource_id is None:
            violations.append(
                f"Timetable record "
                f"{record.timetable_record_id} has no resource/platform assigned."
            )
            return False, violations

        if not self.check_platform_exists(record):
            violations.append(
                f"Platform/resource {record.resource_id} "
                f"does not exist at station "
                f"{record.station_code}."
            )
            return False, violations

        try:
            candidate_allocation = (
                self.get_candidate_allocation(
                    record,
                    buffer_minutes,
                )
            )
        except ValueError as error:
            violations.append(str(error))
            return False, violations

        # Active disruption validation.
        has_disruption_conflict, disruption_violations = (
            self.check_disruption_conflict(
                record,
                candidate_allocation,
            )
        )

        if has_disruption_conflict:
            violations.extend(
                disruption_violations
            )

        # Existing/candidate resource conflict validation.
        has_conflict, conflicts = (
            self.check_platform_conflict(
                record,
                candidate_allocation,
                solution,
            )
        )

        if has_conflict:
            violations.extend(conflicts)

        return len(violations) == 0, violations

    def check_solution(
        self,
        solution: ALNSSolution,
        buffer_minutes: int | None = None,
    ) -> tuple[bool, dict[int, list[str]]]:
        """
        Check candidate solution feasibility.

        Validation scope:
        1. Unrepaired records are infeasible.
        2. Modified records receive full feasibility validation.
        3. Unchanged records on the disrupted resource are checked only
           against the active disruption.
        4. Unchanged unrelated records are not revalidated against the
           existing baseline timetable.

        This prevents pre-existing baseline conflicts from being treated
        as newly introduced candidate conflicts.
        """

        all_violations: dict[int, list[str]] = {}

        for record in solution.records.values():

            # -----------------------------------------------------
            # 1. Unrepaired record
            # -----------------------------------------------------
            if (
                record.resource_id is None
                and record.original_resource_id is not None
            ):
                all_violations[
                    record.timetable_record_id
                ] = [
                    f"Record {record.timetable_record_id} "
                    f"for train {record.train_number} has no "
                    f"assigned resource (unrepaired)."
                ]
                continue

            # -----------------------------------------------------
            # 2. Determine whether the record was modified
            # -----------------------------------------------------
            changed = (
                record.arrival != record.original_arrival
                or record.departure != record.original_departure
                or record.resource_id != record.original_resource_id
                or record.platform_number != record.original_platform_number
            )

            # -----------------------------------------------------
            # 3. Determine whether unchanged record is using the
            #    active disrupted resource
            # -----------------------------------------------------
            disruption_affected = False

            if self.disruption is not None:
                disruption_station = getattr(
                    self.disruption,
                    "station_code",
                    None,
                )

                disruption_resource = getattr(
                    self.disruption,
                    "resource_id",
                    None,
                )

                if (
                    disruption_station is not None
                    and disruption_resource is not None
                    and record.station_code == disruption_station
                    and record.resource_id == disruption_resource
                ):
                    disruption_affected = True

            # -----------------------------------------------------
            # 4. Ignore unrelated unchanged baseline records.
            # -----------------------------------------------------
            if not changed and not disruption_affected:
                continue

            # -----------------------------------------------------
            # 5. Modified records receive complete validation.
            # -----------------------------------------------------
            if changed:
                is_feasible, violations = self.check_record(
                    record,
                    solution,
                    buffer_minutes,
                )

                if not is_feasible:
                    all_violations[
                        record.timetable_record_id
                    ] = violations

                continue

            # -----------------------------------------------------
            # 6. Unchanged record on disrupted resource.
            #
            # Only check active disruption overlap.
            # Do NOT check baseline platform conflicts because those
            # conflicts already existed before this recovery.
            # -----------------------------------------------------
            candidate_allocation = self.get_candidate_allocation(
                record,
                buffer_minutes,
            )

            has_disruption_conflict, violations = (
                self.check_disruption_conflict(
                    record,
                    candidate_allocation,
                )
            )

            if has_disruption_conflict:
                all_violations[
                    record.timetable_record_id
                ] = violations

        return len(all_violations) == 0, all_violations


if __name__ == "__main__":
    from src.optimization.alns_candidate import CandidateBuilder
    from src.optimization.alns_data_loader import load_initial_solution
    from src.optimization.alns_disruption import Disruption
    from src.optimization.alns_move import TimetableModification

    solution = load_initial_solution()

    record_id = 9033

    original_record = solution.get_record(
        record_id
    )

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

    disruption = Disruption(
        disruption_type="PLATFORM_CLOSURE",
        station_code="MAS",
        resource_id="MAS-P4",
        start_time="15:00:00",
        end_time="16:00:00",
        day=1,
    )

    checker = FeasibilityChecker(
        disruption=disruption
    )

    record = candidate.get_record(
        record_id
    )

    print("ALNS feasibility check")
    print("----------------------")

    print(
        f"Train       : {record.train_number}"
    )
    print(
        f"Original    : {original_record.resource_id}"
    )
    print(
        f"Candidate   : {record.resource_id}"
    )

    original_allocation = (
        checker.get_original_allocation(
            original_record
        )
    )

    print("\nOriginal allocation baseline:")
    print(
        f"  Start      : "
        f"{original_allocation.allocation_start}"
    )
    print(
        f"  End        : "
        f"{original_allocation.allocation_end}"
    )
    print(
        f"  Occupancy  : "
        f"{original_allocation.occupancy_minutes} minutes"
    )
    print(
        f"  Buffer     : "
        f"{original_allocation.buffer_minutes} minutes"
    )
    print(
        f"  Release    : "
        f"{original_allocation.release_time}"
    )

    candidate_allocation = (
        checker.get_candidate_allocation(
            record
        )
    )

    print("\nCandidate allocation:")
    print(
        f"  Start      : "
        f"{candidate_allocation.allocation_start}"
    )
    print(
        f"  End        : "
        f"{candidate_allocation.allocation_end}"
    )
    print(
        f"  Occupancy  : "
        f"{candidate_allocation.occupancy_minutes} minutes"
    )
    print(
        f"  Buffer     : "
        f"{candidate_allocation.buffer_minutes} minutes"
    )
    print(
        f"  Release    : "
        f"{candidate_allocation.release_time}"
    )

    platform_exists = (
        checker.check_platform_exists(
            record
        )
    )

    is_feasible, violations = (
        checker.check_record(
            record,
            candidate,
        )
    )

    print(
        f"\nPlatform exists : "
        f"{'PASS' if platform_exists else 'FAIL'}"
    )

    print(
        f"Candidate feasible : "
        f"{'PASS' if is_feasible else 'FAIL'}"
    )

    if violations:
        print("\nViolations:")

        for violation in violations:
            print(
                f"  - {violation}"
            )

    print("\nMinimum recovery buffer:")
    print(
        f"  {MIN_RECOVERY_BUFFER_MINUTES} minutes"
    )