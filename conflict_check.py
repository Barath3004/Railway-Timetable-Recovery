import sqlite3
from datetime import datetime, timedelta

DB_PATH = "data/database/railway_recovery.db"

db = sqlite3.connect(DB_PATH)

rows = db.execute("""
    SELECT
        allocation_id,
        resource_id,
        timetable_record_id,
        day,
        allocation_start,
        allocation_end,
        occupancy_minutes,
        buffer_minutes,
        release_time
    FROM resource_allocations
    ORDER BY resource_id, day, allocation_start
""").fetchall()

def to_minutes(t):
    h, m, s = map(int, t.split(":"))
    return h * 60 + m + s / 60

# Convert each allocation into an operational interval:
# allocation_start -> release_time
intervals = []

for row in rows:
    (
        allocation_id,
        resource_id,
        timetable_record_id,
        day,
        start,
        end,
        occupancy,
        buffer,
        release
    ) = row

    if not start or not end:
        continue

    start_min = to_minutes(start)
    end_min = to_minutes(end)
    release_min = to_minutes(release) if release else end_min

    # Midnight rollover
    if end_min < start_min:
        end_min += 1440

    while release_min < end_min:
        release_min += 1440

    intervals.append({
        "allocation_id": allocation_id,
        "resource_id": resource_id,
        "timetable_record_id": timetable_record_id,
        "day": day,
        "start": start_min,
        "end": end_min,
        "release": release_min,
        "occupancy": occupancy,
        "buffer": buffer
    })

# Compare allocations using the same physical resource and day.
conflicts = []

for i in range(len(intervals)):
    a = intervals[i]

    for j in range(i + 1, len(intervals)):
        b = intervals[j]

        if a["resource_id"] != b["resource_id"]:
            continue

        if a["day"] != b["day"]:
            continue

        # Since sorted by resource/day/start, we can stop early.
        if b["start"] > a["release"]:
            break

        # Operational overlap:
        # one allocation has not released the resource
        # before the next one starts.
        if b["start"] < a["release"] and a["start"] < b["release"]:

            # Ignore exact same timetable record
            if a["timetable_record_id"] == b["timetable_record_id"]:
                continue

            conflicts.append((a, b))

print()
print("========================================")
print("     OPERATIONAL RESOURCE CONFLICTS")
print("========================================")

print("Total allocations:", len(rows))
print("Operational conflicts:", len(conflicts))

resources = {}

for a, b in conflicts:
    resources.setdefault(a["resource_id"], 0)
    resources[a["resource_id"]] += 1

print("Resources with conflicts:", len(resources))

print()
print("=== CONFLICTS BY RESOURCE ===")

for resource, count in sorted(
    resources.items(),
    key=lambda x: x[1],
    reverse=True
):
    print(resource, ":", count)

print()
print("=== FIRST 50 OPERATIONAL CONFLICTS ===")

for number, (a, b) in enumerate(conflicts[:50], 1):

    print()
    print(f"CONFLICT #{number}")
    print(
        a["resource_id"],
        "| Day", a["day"]
    )

    print(
        " A:",
        a["allocation_id"],
        "| timetable", a["timetable_record_id"],
        "|", a["start"],
        "->", a["release"],
        "| occupancy", a["occupancy"],
        "| buffer", a["buffer"]
    )

    print(
        " B:",
        b["allocation_id"],
        "| timetable", b["timetable_record_id"],
        "|", b["start"],
        "->", b["release"],
        "| occupancy", b["occupancy"],
        "| buffer", b["buffer"]
    )

print()
print("========================================")
print("CONFLICT CHECK COMPLETE")
print("========================================")

db.close()