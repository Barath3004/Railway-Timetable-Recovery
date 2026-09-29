
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "database" / "railway_recovery.db"

connection = sqlite3.connect(
    f"file:{DB_PATH.as_posix()}?mode=ro",
    uri=True
)

query = """
SELECT
    timetable_record_id,
    resource_id,
    allocation_start,
    allocation_end,
    release_time
FROM resource_allocations
WHERE station_code = ?
  AND day = ?
  AND allocation_start BETWEEN ? AND ?
ORDER BY allocation_start
"""

rows = connection.execute(
    query,
    ("MS", 1, "04:30:00", "05:30:00")
).fetchall()

print("\nMS PLATFORM ALLOCATIONS — DAY 1")
print("=" * 85)

for record_id, resource, start, end, release in rows:
    print(
        f"Record: {record_id} | "
        f"Platform: {resource} | "
        f"Start: {start} | "
        f"End: {end} | "
        f"Release: {release}"
    )

print("=" * 85)
print(f"Total allocations: {len(rows)}")

connection.close()