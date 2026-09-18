import json
import os
from collections import defaultdict


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RESOURCE_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "resource",
    "resource_allocation.json"
)


# ============================================================
# HELPERS
# ============================================================

def parse_time_to_minutes(value):
    """
    Convert HH:MM:SS into minutes from midnight.

    Returns:
        float | None
    """

    if value is None:
        return None

    value = str(value).strip()

    if value.lower() == "none" or value == "":
        return None

    try:
        parts = value.split(":")

        if len(parts) != 3:
            return None

        hour = int(parts[0])
        minute = int(parts[1])
        second = int(parts[2])

        if not (0 <= hour <= 23):
            return None

        if not (0 <= minute <= 59):
            return None

        if not (0 <= second <= 59):
            return None

        return (
            hour * 60
            + minute
            + second / 60
        )

    except (ValueError, TypeError):
        return None


def absolute_minutes(day, time_value):
    """
    Convert day + HH:MM:SS into absolute minutes.

    Day 1 00:00 = 0
    Day 1 12:00 = 720
    Day 2 00:00 = 1440
    """

    if day is None:
        return None

    try:
        day = int(day)
    except (ValueError, TypeError):
        return None

    if day < 1:
        return None

    time_minutes = parse_time_to_minutes(time_value)

    if time_minutes is None:
        return None

    return (
        (day - 1) * 1440
        + time_minutes
    )


def intervals_overlap(start_a, end_a, start_b, end_b):
    """
    Check whether two half-open intervals overlap.

    [start, end)

    Boundary touching is NOT a conflict.

    Example:
        A = 10:00 -> 10:20
        B = 10:20 -> 10:40

        Result = False
    """

    return (
        start_a < end_b
        and start_b < end_a
    )


def format_absolute_minutes(value):
    """
    Convert absolute minutes back into:
        Day X HH:MM
    """

    if value is None:
        return "UNKNOWN"

    day = int(value // 1440) + 1

    minutes_in_day = value % 1440

    hour = int(minutes_in_day // 60)
    minute = int(minutes_in_day % 60)

    return f"Day {day} {hour:02d}:{minute:02d}"


# ============================================================
# LOAD RESOURCE ALLOCATION
# ============================================================

print("=" * 75)
print("RESOURCE CONFLICT CHECKER - DAY AWARE")
print("=" * 75)
print()

if not os.path.exists(RESOURCE_FILE):
    raise FileNotFoundError(
        f"Resource allocation file not found:\n{RESOURCE_FILE}"
    )


with open(
    RESOURCE_FILE,
    "r",
    encoding="utf-8"
) as file:

    allocations = json.load(file)


if not isinstance(allocations, list):
    raise ValueError(
        "resource_allocation.json must contain a JSON array."
    )


print(
    f"Resource Allocation Records : {len(allocations)}"
)


# ============================================================
# DATA VALIDATION
# ============================================================

print()
print("=" * 75)
print("DATA VALIDATION")
print("=" * 75)
print()


validation_errors = []

duplicate_allocation_ids = []
seen_allocation_ids = set()

invalid_days = []
missing_start_times = []
missing_end_times = []
missing_release_times = []

invalid_intervals = []
invalid_release_intervals = []

for allocation in allocations:

    allocation_id = allocation.get(
        "allocation_id"
    )

    # --------------------------------------------------------
    # Duplicate allocation ID
    # --------------------------------------------------------

    if allocation_id:

        if allocation_id in seen_allocation_ids:

            duplicate_allocation_ids.append(
                allocation_id
            )

        else:

            seen_allocation_ids.add(
                allocation_id
            )

    # --------------------------------------------------------
    # Validate days
    # --------------------------------------------------------

    start_day = allocation.get("day")
    end_day = allocation.get("allocation_end_day")
    release_day = allocation.get("release_day")

    try:
        start_day_int = int(start_day)
        end_day_int = int(end_day)
        release_day_int = int(release_day)

        if (
            start_day_int < 1
            or end_day_int < 1
            or release_day_int < 1
        ):
            raise ValueError

    except (ValueError, TypeError):

        invalid_days.append(
            {
                "allocation_id": allocation_id,
                "day": start_day,
                "allocation_end_day": end_day,
                "release_day": release_day
            }
        )

        continue

    # --------------------------------------------------------
    # Validate times
    # --------------------------------------------------------

    start_time = allocation.get(
        "allocation_start"
    )

    end_time = allocation.get(
        "allocation_end"
    )

    release_time = allocation.get(
        "release_time"
    )

    start = absolute_minutes(
        start_day_int,
        start_time
    )

    end = absolute_minutes(
        end_day_int,
        end_time
    )

    release = absolute_minutes(
        release_day_int,
        release_time
    )

    if start is None:
        missing_start_times.append(
            allocation_id
        )
        continue

    if end is None:
        missing_end_times.append(
            allocation_id
        )
        continue

    if release is None:
        missing_release_times.append(
            allocation_id
        )
        continue

    # --------------------------------------------------------
    # Validate allocation interval
    # --------------------------------------------------------

    if end < start:

        invalid_intervals.append(
            {
                "allocation_id": allocation_id,
                "start": start,
                "end": end
            }
        )

    # --------------------------------------------------------
    # Release must not occur before allocation end
    # --------------------------------------------------------

    if release < end:

        invalid_release_intervals.append(
            {
                "allocation_id": allocation_id,
                "end": end,
                "release": release
            }
        )


# ============================================================
# PRINT VALIDATION RESULTS
# ============================================================

print(
    f"Duplicate Allocation IDs : "
    f"{len(duplicate_allocation_ids)}"
)

print(
    f"Invalid Day Records      : "
    f"{len(invalid_days)}"
)

print(
    f"Missing Start Times      : "
    f"{len(missing_start_times)}"
)

print(
    f"Missing End Times        : "
    f"{len(missing_end_times)}"
)

print(
    f"Missing Release Times    : "
    f"{len(missing_release_times)}"
)

print(
    f"Invalid Intervals        : "
    f"{len(invalid_intervals)}"
)

print(
    f"Release Before End       : "
    f"{len(invalid_release_intervals)}"
)


# ============================================================
# GROUP BY RESOURCE
# ============================================================

resources = defaultdict(list)

for allocation in allocations:

    resource_id = allocation.get(
        "resource_id"
    )

    if not resource_id:
        continue

    start = absolute_minutes(
        allocation.get("day"),
        allocation.get("allocation_start")
    )

    release = absolute_minutes(
        allocation.get("release_day"),
        allocation.get("release_time")
    )

    if start is None or release is None:
        continue

    # Ignore completely invalid intervals.
    if release < start:
        continue

    allocation["_absolute_start"] = start
    allocation["_absolute_release"] = release

    resources[resource_id].append(
        allocation
    )


# ============================================================
# SORT RESOURCE ALLOCATIONS
# ============================================================

for resource_id in resources:

    resources[resource_id].sort(
        key=lambda allocation: (
            allocation["_absolute_start"],
            allocation["_absolute_release"]
        )
    )


# ============================================================
# CONFLICT DETECTION
# ============================================================

conflicts = []

checked_pairs = 0

for resource_id, resource_records in resources.items():

    for i in range(
        len(resource_records)
    ):

        a = resource_records[i]

        start_a = a["_absolute_start"]
        end_a = a["_absolute_release"]

        # ----------------------------------------------------
        # Compare only records after A.
        # Because records are sorted by start time.
        # ----------------------------------------------------

        for j in range(
            i + 1,
            len(resource_records)
        ):

            b = resource_records[j]

            start_b = b["_absolute_start"]
            end_b = b["_absolute_release"]

            # ------------------------------------------------
            # Optimization:
            #
            # If B starts at or after A's release,
            # later records cannot overlap A either.
            # ------------------------------------------------

            if start_b >= end_a:
                break

            checked_pairs += 1

            if intervals_overlap(
                start_a,
                end_a,
                start_b,
                end_b
            ):

                conflicts.append(
                    {
                        "resource_id": resource_id,

                        "allocation_a": {
                            "allocation_id":
                                a.get(
                                    "allocation_id"
                                ),

                            "timetable_record_id":
                                a.get(
                                    "timetable_record_id"
                                ),

                            "day":
                                a.get(
                                    "day"
                                ),

                            "allocation_end_day":
                                a.get(
                                    "allocation_end_day"
                                ),

                            "release_day":
                                a.get(
                                    "release_day"
                                ),

                            "allocation_start":
                                a.get(
                                    "allocation_start"
                                ),

                            "allocation_end":
                                a.get(
                                    "allocation_end"
                                ),

                            "release_time":
                                a.get(
                                    "release_time"
                                ),

                            "absolute_start":
                                start_a,

                            "absolute_release":
                                end_a
                        },

                        "allocation_b": {
                            "allocation_id":
                                b.get(
                                    "allocation_id"
                                ),

                            "timetable_record_id":
                                b.get(
                                    "timetable_record_id"
                                ),

                            "day":
                                b.get(
                                    "day"
                                ),

                            "allocation_end_day":
                                b.get(
                                    "allocation_end_day"
                                ),

                            "release_day":
                                b.get(
                                    "release_day"
                                ),

                            "allocation_start":
                                b.get(
                                    "allocation_start"
                                ),

                            "allocation_end":
                                b.get(
                                    "allocation_end"
                                ),

                            "release_time":
                                b.get(
                                    "release_time"
                                ),

                            "absolute_start":
                                start_b,

                            "absolute_release":
                                end_b
                        }
                    }
                )


# ============================================================
# RESOURCE-WISE CONFLICT SUMMARY
# ============================================================

conflict_resources = defaultdict(int)

for conflict in conflicts:

    conflict_resources[
        conflict["resource_id"]
    ] += 1


# ============================================================
# CROSS-DAY CONFLICTS
# ============================================================

cross_day_conflicts = []

for conflict in conflicts:

    a = conflict["allocation_a"]
    b = conflict["allocation_b"]

    if (
        a["day"] != b["day"]
        or a["allocation_end_day"] != b["allocation_end_day"]
        or a["release_day"] != b["release_day"]
    ):

        cross_day_conflicts.append(
            conflict
        )


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 75)
print("RESOURCE CONFLICT RESULTS")
print("=" * 75)
print()

print(
    f"Platform Resources Checked : "
    f"{len(resources)}"
)

print(
    f"Allocation Pairs Checked   : "
    f"{checked_pairs}"
)

print(
    f"Resource Conflicts         : "
    f"{len(conflicts)}"
)

print(
    f"Resources With Conflicts   : "
    f"{len(conflict_resources)}"
)

print(
    f"Cross-Day Conflicts        : "
    f"{len(cross_day_conflicts)}"
)


# ============================================================
# PRINT CONFLICT DETAILS
# ============================================================

if conflicts:

    print()
    print("=" * 75)
    print(
        f"CONFLICT DETAILS "
        f"(SHOWING FIRST {min(100, len(conflicts))})"
    )
    print("=" * 75)

    for index, conflict in enumerate(
        conflicts[:100],
        start=1
    ):

        a = conflict["allocation_a"]
        b = conflict["allocation_b"]

        print()
        print(
            f"CONFLICT #{index}"
        )

        print(
            f"RESOURCE : "
            f"{conflict['resource_id']}"
        )

        print(
            f"A        : "
            f"{a['allocation_id']} | "
            f"Timetable {a['timetable_record_id']}"
        )

        print(
            f"           "
            f"Day {a['day']} "
            f"{a['allocation_start']} -> "
            f"Day {a['release_day']} "
            f"{a['release_time']}"
        )

        print(
            f"           "
            f"Absolute: "
            f"{format_absolute_minutes(a['absolute_start'])}"
            f" -> "
            f"{format_absolute_minutes(a['absolute_release'])}"
        )

        print(
            f"B        : "
            f"{b['allocation_id']} | "
            f"Timetable {b['timetable_record_id']}"
        )

        print(
            f"           "
            f"Day {b['day']} "
            f"{b['allocation_start']} -> "
            f"Day {b['release_day']} "
            f"{b['release_time']}"
        )

        print(
            f"           "
            f"Absolute: "
            f"{format_absolute_minutes(b['absolute_start'])}"
            f" -> "
            f"{format_absolute_minutes(b['absolute_release'])}"
        )

        print(
            "STATUS   : CONFLICT"
        )

else:

    print()
    print(
        "NO RESOURCE CONFLICTS FOUND."
    )


# ============================================================
# RESOURCE-WISE SUMMARY
# ============================================================

if conflict_resources:

    print()
    print("=" * 75)
    print("RESOURCE-WISE CONFLICT SUMMARY")
    print("=" * 75)

    for resource_id, count in sorted(
        conflict_resources.items(),
        key=lambda item: item[1],
        reverse=True
    ):

        print(
            f"{resource_id:<15} : {count}"
        )


# ============================================================
# DATA QUALITY WARNINGS
# ============================================================

if (
    duplicate_allocation_ids
    or invalid_days
    or missing_start_times
    or missing_end_times
    or missing_release_times
    or invalid_intervals
    or invalid_release_intervals
):

    print()
    print("=" * 75)
    print("DATA QUALITY STATUS")
    print("=" * 75)

    print()
    print(
        "WARNING: Data quality issues were detected."
    )

    print(
        "Resolve these before freezing the dataset "
        "for SQLite/ALNS."
    )

else:

    print()
    print("=" * 75)
    print("DATA QUALITY STATUS")
    print("=" * 75)

    print()
    print(
        "ALL RESOURCE ALLOCATION RECORDS PASSED "
        "BASIC DATA VALIDATION."
    )


# ============================================================
# FINAL INTERPRETATION
# ============================================================

print()
print("=" * 75)
print("INTERPRETATION")
print("=" * 75)
print()

if conflicts:

    print(
        "RESOURCE CONFLICTS EXIST."
    )

    print(
        "The conflicts represent overlapping occupancy "
        "intervals on the same physical resource."
    )

    print(
        "Do NOT move to SQLite/ALNS yet."
    )

    print(
        "First inspect the reported conflicting allocations "
        "and determine whether the platform allocator or "
        "the source timetable requires correction."
    )

else:

    print(
        "NO RESOURCE CONFLICTS FOUND."
    )

    print(
        "The current timetable/resource allocation is "
        "resource-feasible under the implemented occupancy "
        "and buffer rules."
    )

    print(
        "The resource allocation JSON can now be treated "
        "as the validated input dataset for SQLite."
    )


# ============================================================
# FILE SAFETY
# ============================================================

print()
print(
    "No files were modified."
)

print()
print("=" * 75)
print("DONE")
print("=" * 75)