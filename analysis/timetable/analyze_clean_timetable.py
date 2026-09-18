"""
Analyze Clean Project Timetable

Purpose
-------
Analyze the cleaned timetable dataset before creating the database.

Author: Barath
"""

import json
import os
from collections import Counter

# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "clean_project_timetable.json"
)
# --------------------------------------------------
# Load Dataset
# --------------------------------------------------

print("=" * 70)
print("PROJECT TIMETABLE ANALYSIS")
print("=" * 70)
print()

with open(INPUT_FILE, "r", encoding="utf-8") as file:
    timetable = json.load(file)

print(f"Total Records : {len(timetable):,}")

# --------------------------------------------------
# Statistics Containers
# --------------------------------------------------

station_counter = Counter()
train_stop_counter = Counter()
start_station_counter = Counter()
end_station_counter = Counter()

arrival_missing = 0
departure_missing = 0

duplicate_counter = Counter()

# --------------------------------------------------
# Collect Statistics
# --------------------------------------------------

for row in timetable:

    train = row["train_number"]
    station = row["station_code"]

    station_counter[station] += 1
    train_stop_counter[train] += 1

    duplicate_counter[(train, station)] += 1

    if row["arrival"] is None:
        arrival_missing += 1

    if row["departure"] is None:
        departure_missing += 1

# --------------------------------------------------
# Start / End Stations
# --------------------------------------------------

train_groups = {}

for row in timetable:

    train = row["train_number"]

    train_groups.setdefault(train, []).append(row)

for train, stops in train_groups.items():

    stops = sorted(
        stops,
        key=lambda x: (
            x["day"] if x["day"] is not None else 0,
            x["departure"] if x["departure"] is not None else "",
            x["arrival"] if x["arrival"] is not None else ""
        )
    )

    start_station_counter[stops[0]["station_code"]] += 1
    end_station_counter[stops[-1]["station_code"]] += 1

# --------------------------------------------------
# Duplicate Station Visits
# --------------------------------------------------

duplicate_visits = sum(
    1
    for value in duplicate_counter.values()
    if value > 1
)

# --------------------------------------------------
# Summary
# --------------------------------------------------

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"Unique Trains          : {len(train_stop_counter):,}")
print(f"Unique Stations        : {len(station_counter):,}")
print(f"Missing Arrival        : {arrival_missing:,}")
print(f"Missing Departure      : {departure_missing:,}")
print(f"Duplicate Station Visit: {duplicate_visits:,}")
print(f"Maximum Stops/Train    : {max(train_stop_counter.values())}")
print(f"Minimum Stops/Train    : {min(train_stop_counter.values())}")
print(f"Average Stops/Train    : {round(sum(train_stop_counter.values()) / len(train_stop_counter),2)}")

# --------------------------------------------------
# Busiest Stations
# --------------------------------------------------

print()
print("=" * 70)
print("TOP 20 BUSIEST STATIONS")
print("=" * 70)

for station, count in station_counter.most_common(20):
    print(f"{station:<10} {count}")

# --------------------------------------------------
# Longest Trains
# --------------------------------------------------

print()
print("=" * 70)
print("TOP 20 LONGEST TRAINS")
print("=" * 70)

for train, count in sorted(
    train_stop_counter.items(),
    key=lambda x: x[1],
    reverse=True
)[:20]:

    print(f"{train:<10} {count}")

# --------------------------------------------------
# Start Stations
# --------------------------------------------------

print()
print("=" * 70)
print("TOP START STATIONS")
print("=" * 70)

for station, count in start_station_counter.most_common(15):
    print(f"{station:<10} {count}")

# --------------------------------------------------
# End Stations
# --------------------------------------------------

print()
print("=" * 70)
print("TOP END STATIONS")
print("=" * 70)

for station, count in end_station_counter.most_common(15):
    print(f"{station:<10} {count}")

# --------------------------------------------------
# Trains with Less Than 3 Stops
# --------------------------------------------------

print()
print("=" * 70)
print("TRAINS WITH FEWER THAN 3 STOPS")
print("=" * 70)

few_stop_found = False

for train, count in sorted(
    train_stop_counter.items(),
    key=lambda x: x[1]
):

    if count < 3:
        few_stop_found = True
        print(f"Train {train:<10} Stops : {count}")

        for row in train_groups[train]:
            print(
                f"   {row['station_code']:<8}"
                f"{row['station_name']:<35}"
                f"Day:{row['day']}  "
                f"Arr:{row['arrival']}  "
                f"Dep:{row['departure']}"
            )

        print("-" * 60)

if not few_stop_found:
    print("No trains found with fewer than 3 stops.")

# --------------------------------------------------
# Analysis Complete
# --------------------------------------------------

print()
print("=" * 70)
print("ANALYSIS COMPLETED")
print("=" * 70)