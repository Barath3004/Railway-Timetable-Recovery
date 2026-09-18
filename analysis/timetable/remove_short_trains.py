"""
Remove Short Trains

Purpose
-------
Remove trains that contain fewer than the minimum number of
stops required for timetable recovery.

For our project, trains having only one or two stations inside
the project corridor are not useful because they cannot create
resource conflicts or delay propagation.

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
    "project_timetable_filtered.json"
)

MIN_STOPS = 3

# --------------------------------------------------
# Load Timetable
# --------------------------------------------------

print("=" * 70)
print("REMOVING SHORT TRAINS")
print("=" * 70)
print()

with open(INPUT_FILE, "r", encoding="utf-8") as file:
    timetable = json.load(file)

print(f"Loaded Records : {len(timetable):,}")

# --------------------------------------------------
# Group by Train
# --------------------------------------------------

trains = {}

for row in timetable:

    train_number = row["train_number"]

    if train_number not in trains:
        trains[train_number] = []

    trains[train_number].append(row)

print(f"Loaded Trains  : {len(trains):,}")

# --------------------------------------------------
# Remove Short Trains
# --------------------------------------------------

filtered_rows = []

removed_trains = 0
removed_records = 0

kept_trains = 0

for train_number, stops in trains.items():

    if len(stops) < MIN_STOPS:

        removed_trains += 1
        removed_records += len(stops)

        continue

    filtered_rows.extend(stops)
    kept_trains += 1

# --------------------------------------------------
# Save Output
# --------------------------------------------------

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(filtered_rows, file, indent=4)

# --------------------------------------------------
# Summary
# --------------------------------------------------

print()
print("=" * 70)
print("SHORT TRAIN REMOVAL COMPLETED")
print("=" * 70)

print(f"Minimum Stops Required : {MIN_STOPS}")
print(f"Removed Trains         : {removed_trains:,}")
print(f"Removed Records        : {removed_records:,}")
print(f"Remaining Trains       : {kept_trains:,}")
print(f"Remaining Records      : {len(filtered_rows):,}")

print()
print("Saved To:")
print(OUTPUT_FILE)