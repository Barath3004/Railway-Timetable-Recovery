"""
Clean Project Timetable

Purpose
-------
Clean the filtered timetable dataset before importing it
into the project database.

Operations Performed
--------------------
1. Convert "None" strings to Python None
2. Trim whitespace
3. Standardize station codes to uppercase
4. Remove duplicate records
5. Sort timetable records
6. Save cleaned timetable

Author: Barath
"""

import json
import os

# --------------------------------------------------
# Project Paths
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "project_timetable.json"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "clean_project_timetable.json"
)

# --------------------------------------------------
# Helper Function
# --------------------------------------------------

def clean_value(value):
    """
    Convert invalid values into Python None.
    """

    if value is None:
        return None

    if isinstance(value, str):

        value = value.strip()

        if value.lower() == "none":
            return None

        if value == "":
            return None

        return value

    return value


# --------------------------------------------------
# Load Dataset
# --------------------------------------------------

print("=" * 70)
print("CLEANING PROJECT TIMETABLE")
print("=" * 70)
print()

with open(INPUT_FILE, "r", encoding="utf-8") as file:
    timetable = json.load(file)

print(f"Loaded Records : {len(timetable):,}")

# --------------------------------------------------
# Clean Records
# --------------------------------------------------

cleaned = []

converted_none = 0

for row in timetable:

    row["arrival"] = clean_value(row.get("arrival"))
    row["departure"] = clean_value(row.get("departure"))
    row["station_name"] = clean_value(row.get("station_name"))
    row["station_code"] = clean_value(row.get("station_code"))
    row["train_name"] = clean_value(row.get("train_name"))
    row["train_number"] = clean_value(row.get("train_number"))

    if row["arrival"] is None:
        converted_none += 1

    if row["departure"] is None:
        converted_none += 1

    if row["station_name"]:
        row["station_name"] = row["station_name"].strip()

    if row["station_code"]:
        row["station_code"] = row["station_code"].strip().upper()

    if row["train_name"]:
        row["train_name"] = row["train_name"].strip()

    if row["train_number"]:
        row["train_number"] = row["train_number"].strip()

    cleaned.append(row)

print(f'Converted "None" Values : {converted_none:,}')

# --------------------------------------------------
# Remove Duplicates
# --------------------------------------------------

unique_records = []
seen = set()

duplicates_removed = 0

for row in cleaned:

    key = (
        row["train_number"],
        row["station_code"],
        row["day"],
        row["arrival"],
        row["departure"]
    )

    if key in seen:
        duplicates_removed += 1
        continue

    seen.add(key)
    unique_records.append(row)

print(f"Duplicates Removed : {duplicates_removed:,}")

# --------------------------------------------------
# Sort Records
# --------------------------------------------------

def sort_time(value):
    if value is None:
        return "99:99:99"
    return value

unique_records.sort(
    key=lambda row: (
        row["train_number"],
        row["day"] if row["day"] is not None else 99,
        sort_time(row["arrival"]),
        sort_time(row["departure"])
    )
)

# --------------------------------------------------
# Save Output
# --------------------------------------------------

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(unique_records, file, indent=4)

# --------------------------------------------------
# Summary
# --------------------------------------------------

print()
print("=" * 70)
print("CLEANING COMPLETED")
print("=" * 70)

print(f"Final Records      : {len(unique_records):,}")

print()
print("Saved To:")
print(OUTPUT_FILE)