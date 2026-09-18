import json
import os
from collections import defaultdict

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
    "timing_validation_report.txt"
)

# ==========================================================
# LOAD DATA
# ==========================================================

print("=" * 70)
print("TIMING VALIDATION")
print("=" * 70)

with open(INPUT_FILE, "r", encoding="utf-8") as file:
    timetable = json.load(file)

print(f"Loaded Records : {len(timetable):,}")

# ==========================================================
# GROUP TRAINS
# ==========================================================

trains = defaultdict(list)

for row in timetable:

    train_no = str(row.get("train_number", "")).strip()

    trains[train_no].append(row)

print(f"Loaded Trains  : {len(trains):,}")

# ==========================================================
# TIME CONVERTER
# Supports:
# HH:MM
# HH:MM:SS
# Handles "None"
# ==========================================================

def time_to_minutes(value):

    if value is None:
        return None

    value = str(value).strip()

    if value in ["", "None"]:
        return None

    if value.upper() in ["--", "NA", "N/A"]:
        return None

    try:

        parts = value.split(":")

        if len(parts) == 2:

            hour, minute = parts

        elif len(parts) == 3:

            hour, minute, second = parts

        else:

            return None

        hour = int(hour)
        minute = int(minute)

        if hour < 0 or hour > 23:
            return None

        if minute < 0 or minute > 59:
            return None

        return hour * 60 + minute

    except:

        return None


# ==========================================================
# SORT HELPER
# ==========================================================

def sort_key(row):

    stop = row.get("stop_number")

    if stop is not None:

        try:

            return (0, int(stop))

        except:

            pass

    day = row.get("day")

    if day is None:

        day = 1

    arr = time_to_minutes(row.get("arrival"))
    dep = time_to_minutes(row.get("departure"))

    if arr is None:
        arr = 9999

    if dep is None:
        dep = 9999

    return (1, int(day), arr, dep)


# ==========================================================
# VARIABLES
# ==========================================================

missing_arrival = 0
missing_departure = 0

invalid_arrival = 0
invalid_departure = 0

suspicious_halt = 0

report = []

# ==========================================================
# VALIDATION
# ==========================================================

for train_no, rows in trains.items():

    rows = sorted(rows, key=sort_key)

    total = len(rows)

    for index, row in enumerate(rows):

        station = row.get("station_code", "")

        arrival = row.get("arrival")
        departure = row.get("departure")

        arr = time_to_minutes(arrival)
        dep = time_to_minutes(departure)

        # ==================================================
        # FIRST STATION
        # Arrival is allowed to be missing
        # ==================================================

        if index == 0:

            if departure in [None, "", "--", "None"]:

                missing_departure += 1

                report.append(
                    f"{train_no} | {station} | Missing Departure"
                )

            elif dep is None:

                invalid_departure += 1

                report.append(
                    f"{train_no} | {station} | Invalid Departure ({departure})"
                )

            continue

        # ==================================================
        # LAST STATION
        # Departure is allowed to be missing
        # ==================================================

        if index == total - 1:

            if arrival in [None, "", "--", "None"]:

                missing_arrival += 1

                report.append(
                    f"{train_no} | {station} | Missing Arrival"
                )

            elif arr is None:

                invalid_arrival += 1

                report.append(
                    f"{train_no} | {station} | Invalid Arrival ({arrival})"
                )

            continue

        # ==================================================
        # INTERMEDIATE STATIONS
        # ==================================================

        # Arrival

        if arrival in [None, "", "--", "None"]:

            missing_arrival += 1

            report.append(
                f"{train_no} | {station} | Missing Arrival"
            )

        elif arr is None:

            invalid_arrival += 1

            report.append(
                f"{train_no} | {station} | Invalid Arrival ({arrival})"
            )

        # Departure

        if departure in [None, "", "--", "None"]:

            missing_departure += 1

            report.append(
                f"{train_no} | {station} | Missing Departure"
            )

        elif dep is None:

            invalid_departure += 1

            report.append(
                f"{train_no} | {station} | Invalid Departure ({departure})"
            )

        # ==================================================
        # Halt Time Check
        # ==================================================

        if arr is not None and dep is not None:

            halt = dep - arr

            # Overnight departure

            if halt < 0:
                halt += 24 * 60

            # More than 6 hours halt is suspicious

            if halt > 360:

                suspicious_halt += 1

                report.append(
                    f"{train_no} | {station} | Suspicious Halt ({halt} min)"
                )

# ==========================================================
# SAVE REPORT
# ==========================================================

summary = []

summary.append("=" * 70)
summary.append("TIMING VALIDATION REPORT")
summary.append("=" * 70)
summary.append("")

summary.append(f"Total Trains         : {len(trains)}")
summary.append(f"Total Records        : {len(timetable)}")
summary.append("")

summary.append(f"Missing Arrival      : {missing_arrival}")
summary.append(f"Missing Departure    : {missing_departure}")
summary.append(f"Invalid Arrival      : {invalid_arrival}")
summary.append(f"Invalid Departure    : {invalid_departure}")
summary.append(f"Suspicious Halt      : {suspicious_halt}")

summary.append("")
summary.append("=" * 70)
summary.append("DETAILS")
summary.append("=" * 70)

summary.extend(report)

with open(REPORT_FILE, "w", encoding="utf-8") as file:
    file.write("\n".join(summary))

# ==========================================================
# PRINT SUMMARY
# ==========================================================

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"Missing Arrival      : {missing_arrival}")
print(f"Missing Departure    : {missing_departure}")
print(f"Invalid Arrival      : {invalid_arrival}")
print(f"Invalid Departure    : {invalid_departure}")
print(f"Suspicious Halt      : {suspicious_halt}")

print()
print("Report Saved To:")
print(REPORT_FILE)

print()
print("=" * 70)
print("TIMING VALIDATION COMPLETED")
print("=" * 70)