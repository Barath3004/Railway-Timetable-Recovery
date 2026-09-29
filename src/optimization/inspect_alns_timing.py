import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "data" / "database" / "railway_recovery.db"


db = sqlite3.connect(DATABASE_PATH)
db.row_factory = sqlite3.Row


print("9033 ALLOCATION")
print("----------------")

rows = db.execute(
    """
    SELECT *
    FROM resource_allocations
    WHERE timetable_record_id = 9033
    """
).fetchall()

for row in rows:
    print(dict(row))


print("\n9033 TIMETABLE")
print("----------------")

rows = db.execute(
    """
    SELECT *
    FROM timetable
    WHERE timetable_record_id = 9033
    """
).fetchall()

for row in rows:
    print(dict(row))


print("\nTRAIN 06001")
print("----------------")

rows = db.execute(
    """
    SELECT *
    FROM timetable
    WHERE train_number = '06001'
    ORDER BY day, stop_number
    """
).fetchall()

for row in rows:
    print(dict(row))


print("\nCONFLICT RECORD 4773")
print("----------------")

rows = db.execute(
    """
    SELECT *
    FROM resource_allocations
    WHERE timetable_record_id = 4773
    """
).fetchall()

for row in rows:
    print(dict(row))


db.close()
