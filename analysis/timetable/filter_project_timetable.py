"""
Filter Project Timetable

Purpose
-------
Extract only the section of every train that belongs to
our project stations.

Example

Train Route:
A -> B -> C -> D -> E -> F -> G

Project Stations:
C, D, E

Output:
C -> D -> E

Author: Barath
"""

import json
import os
import sys

# --------------------------------------------------
# Project Paths
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")

# Add "data" folder to Python import path
sys.path.append(DATA_DIR)

from config.project_stations import PROJECT_STATIONS

INPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "raw",
    "schedules.json"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "project_timetable.json"
)

# --------------------------------------------------
# Display Project Information
# --------------------------------------------------

print("=" * 70)
print("READING MASTER TIMETABLE")
print("=" * 70)

print(f"Project Stations : {len(PROJECT_STATIONS)}")

# --------------------------------------------------
# Load Master Timetable
# --------------------------------------------------

with open(INPUT_FILE, "r", encoding="utf-8") as file:
    timetable = json.load(file)

print(f"Total Records    : {len(timetable):,}")

# --------------------------------------------------
# Group Stops by Train
# --------------------------------------------------

trains = {}

for row in timetable:

    train_number = row["train_number"]

    if train_number not in trains:
        trains[train_number] = []

    trains[train_number].append(row)

print(f"Unique Trains    : {len(trains):,}")

print()
print("Filtering trains...")
print()

# --------------------------------------------------
# Filter Route
# --------------------------------------------------

filtered_rows = []
included_trains = 0

project_station_set = set(PROJECT_STATIONS)

for train_number, stops in trains.items():

    project_indexes = []

    for index, stop in enumerate(stops):

        if stop["station_code"] in project_station_set:
            project_indexes.append(index)

    # Skip trains that never enter project stations
    if not project_indexes:
        continue

    start_index = min(project_indexes)
    end_index = max(project_indexes)

    filtered_rows.extend(stops[start_index:end_index + 1])

    included_trains += 1

# --------------------------------------------------
# Save Output
# --------------------------------------------------

print("Saving project dataset...")

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(filtered_rows, file, indent=4)

# --------------------------------------------------
# Summary
# --------------------------------------------------

print()
print("=" * 70)
print("FILTER COMPLETED")
print("=" * 70)

print(f"Selected Trains : {included_trains:,}")
print(f"Selected Records: {len(filtered_rows):,}")

print()
print("Saved To:")
print(OUTPUT_FILE)