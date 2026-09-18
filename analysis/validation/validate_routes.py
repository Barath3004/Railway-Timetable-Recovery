import json
import os
from collections import defaultdict, Counter

# ==========================================================
# PATHS
# ==========================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "project_timetable_cleaned.json"
)

REPORT_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

REPORT_FILE = os.path.join(
    REPORT_DIR,
    "route_validation_report.txt"
)

# ==========================================================
# LOAD DATA
# ==========================================================

print("=" * 70)
print("ROUTE VALIDATION")
print("=" * 70)

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    timetable = json.load(f)

print(f"Loaded Records : {len(timetable):,}")

# ==========================================================
# GROUP BY TRAIN
# ==========================================================

trains = defaultdict(list)

for row in timetable:
    train_no = str(row.get("train_number", "")).strip()
    trains[train_no].append(row)

print(f"Loaded Trains  : {len(trains):,}")

# ==========================================================
# SAFE FUNCTIONS
# ==========================================================

def safe_int(value, default=999999):
    try:
        if value is None:
            return default

        value = str(value).strip()

        if value == "":
            return default

        return int(value)

    except:
        return default


# ==========================================================
# REPORT VARIABLES
# ==========================================================

duplicate_station_trains = []
duplicate_stop_trains = []
circular_routes = []

longest_train = ""
longest_stop_count = 0

shortest_train = ""
shortest_stop_count = 999999

total_stops = 0

details = []

# ==========================================================
# VALIDATION
# ==========================================================

for train_no, rows in trains.items():

    # ---------------------------------------
    # Preserve original order whenever possible
    # ---------------------------------------

    if "stop_number" in rows[0]:

        rows.sort(
            key=lambda x: safe_int(
                x.get("stop_number"),
                999999
            )
        )

    stop_count = len(rows)

    total_stops += stop_count

    if stop_count > longest_stop_count:
        longest_stop_count = stop_count
        longest_train = train_no

    if stop_count < shortest_stop_count:
        shortest_stop_count = stop_count
        shortest_train = train_no

    # ---------------------------------------
    # Duplicate Stations
    # ---------------------------------------

    station_codes = []

    for row in rows:

        code = str(
            row.get("station_code", "")
        ).strip()

        station_codes.append(code)

    station_counter = Counter(station_codes)

    duplicates = []

    for station, count in station_counter.items():

        if count > 1:
            duplicates.append(station)

    if duplicates:

        duplicate_station_trains.append(train_no)

        details.append("")
        details.append(f"Train : {train_no}")
        details.append("Duplicate Stations:")

        for station in duplicates:
            details.append(f"   {station}")

    # ---------------------------------------
    # Duplicate Stop Numbers
    # ---------------------------------------

    stop_numbers = []

    for row in rows:

        stop = row.get("stop_number")

        if stop is not None:
            stop_numbers.append(stop)

    if len(stop_numbers):

        stop_counter = Counter(stop_numbers)

        repeated = False

        for value in stop_counter.values():

            if value > 1:
                repeated = True
                break

        if repeated:

            duplicate_stop_trains.append(train_no)

            details.append("")
            details.append(f"Train : {train_no}")
            details.append("Duplicate Stop Numbers")

    # ---------------------------------------
    # Circular Route
    # ---------------------------------------

    if len(station_codes) >= 3:

        if station_codes[0] == station_codes[-1]:

            circular_routes.append(train_no)

            details.append("")
            details.append(
                f"Train {train_no} appears circular "
                f"({station_codes[0]})"
            )

# ==========================================================
# SUMMARY
# ==========================================================

average_stops = total_stops / len(trains)

summary = []

summary.append("=" * 70)
summary.append("ROUTE VALIDATION REPORT")
summary.append("=" * 70)
summary.append("")

summary.append(f"Total Trains             : {len(trains)}")
summary.append(f"Total Records            : {len(timetable)}")
summary.append("")

summary.append(
    f"Duplicate Station Routes : {len(duplicate_station_trains)}"
)

summary.append(
    f"Duplicate Stop Numbers   : {len(duplicate_stop_trains)}"
)

summary.append(
    f"Circular Routes          : {len(circular_routes)}"
)

summary.append("")

summary.append(
    f"Longest Route            : {longest_train} ({longest_stop_count} stops)"
)

summary.append(
    f"Shortest Route           : {shortest_train} ({shortest_stop_count} stops)"
)

summary.append(
    f"Average Stops            : {average_stops:.2f}"
)

summary.append("")
summary.append("=" * 70)
summary.append("DETAILS")
summary.append("=" * 70)

summary.extend(details)

# ==========================================================
# SAVE REPORT
# ==========================================================

with open(REPORT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(summary))

# ==========================================================
# PRINT
# ==========================================================

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"Duplicate Station Routes : {len(duplicate_station_trains)}")
print(f"Duplicate Stop Numbers   : {len(duplicate_stop_trains)}")
print(f"Circular Routes          : {len(circular_routes)}")
print()

print(f"Longest Route            : {longest_train} ({longest_stop_count} stops)")
print(f"Shortest Route           : {shortest_train} ({shortest_stop_count} stops)")
print(f"Average Stops            : {average_stops:.2f}")

print()
print("Report Saved To:")
print(REPORT_FILE)

print()
print("=" * 70)
print("ROUTE VALIDATION COMPLETED")
print("=" * 70)