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
    ORDER BY allocation_id
""").fetchall()

zero_duration = []
duration_mismatch = []
release_problem = []
cross_midnight = []

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

    start_dt = datetime.strptime(start, "%H:%M:%S")
    end_dt = datetime.strptime(end, "%H:%M:%S")

    # Handle midnight rollover
    if end_dt < start_dt:
        end_dt += timedelta(days=1)
        cross_midnight.append(row)

    duration = int(
        (end_dt - start_dt).total_seconds() / 60
    )

    if duration == 0:
        zero_duration.append(row)

    if duration != occupancy:
        duration_mismatch.append(
            (
                allocation_id,
                start,
                end,
                duration,
                occupancy
            )
        )

    if release:
        release_dt = datetime.strptime(
            release,
            "%H:%M:%S"
        )

        # Handle release after midnight
        while release_dt < end_dt:
            release_dt += timedelta(days=1)

        expected_release = end_dt + timedelta(
            minutes=buffer or 0
        )

        if release_dt != expected_release:
            release_problem.append(
                (
                    allocation_id,
                    end,
                    buffer,
                    release,
                    expected_release.strftime("%H:%M:%S")
                )
            )

print()
print("========================================")
print("       IMPROVED TIMING VALIDATION")
print("========================================")

print("Total allocations:", len(rows))
print("Zero-duration:", len(zero_duration))
print("Cross-midnight:", len(cross_midnight))
print("Occupancy mismatches:", len(duration_mismatch))
print("Release-time mismatches:", len(release_problem))

print()
print("=== FIRST 30 OCCUPANCY MISMATCHES ===")

for row in duration_mismatch[:30]:
    print(row)

print()
print("=== CROSS-MIDNIGHT ALLOCATIONS ===")

for row in cross_midnight:
    print(row)

print()
print("=== FIRST 30 RELEASE-TIME MISMATCHES ===")

for row in release_problem[:30]:
    print(row)

print()
print("========================================")
print("VALIDATION COMPLETE")
print("========================================")

db.close()