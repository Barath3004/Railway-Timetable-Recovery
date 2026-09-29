import sqlite3
from pathlib import Path

DB_PATH = Path("data/database/railway_recovery.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("MS PLATFORM OCCUPANCY: 04:40-05:40")
print("=" * 80)

rows = cursor.execute("""
    SELECT
        timetable_record_id,
        train_number,
        platform_number,
        arrival,
        departure
    FROM timetable
    WHERE station_code = 'MS'
      AND platform_number IS NOT NULL
      AND arrival < '05:40:00'
      AND COALESCE(departure, arrival) > '04:40:00'
    ORDER BY platform_number, arrival
""").fetchall()

for row in rows:
    print(row)

conn.close()