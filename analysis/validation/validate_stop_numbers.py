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
    "project_timetable_ordered.json"
)

REPORT_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

REPORT_FILE = os.path.join(
    REPORT_DIR,
    "stop_number_validation_report.txt"
)

# ==========================================================
# LOAD DATA
# ==========================================================

print("=" * 70)
print("STOP NUMBER VALIDATION")
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
# VARIABLES
# ==========================================================

missing_stop_number = 0
duplicate_stop_numbers = 0
non_continuous_routes = 0
invalid_first_stop = 0
invalid_last_stop = 0

report = []

# ==========================================================
# VALIDATE
# ==========================================================

for train_no, rows in trains.items():

    stops = []

    for row in rows:

        stop = row.get("stop_number")

        if stop is None:

            missing_stop_number += 1

            report.append(
                f"{train_no} | Missing stop_number"
            )

            continue

        try:
            stop = int(stop)
            stops.append(stop)

        except:

            missing_stop_number += 1

            report.append(
                f"{train_no} | Invalid stop_number ({stop})"
            )

    if len(stops) == 0:
        continue

    # ------------------------------------
    # Duplicate stop numbers
    # ------------------------------------

    if len(stops) != len(set(stops)):

        duplicate_stop_numbers += 1

        report.append(
            f"{train_no} | Duplicate stop numbers"
        )

    # ------------------------------------
    # Starts from 1
    # ------------------------------------

    if min(stops) != 1:

        invalid_first_stop += 1

        report.append(
            f"{train_no} | Starts from {min(stops)} instead of 1"
        )

    # ------------------------------------
    # Continuous numbering
    # ------------------------------------

    expected = list(range(1, len(stops) + 1))

    if sorted(stops) != expected:

        non_continuous_routes += 1

        missing = sorted(set(expected) - set(stops))
        extra = sorted(set(stops) - set(expected))

        report.append(
            f"{train_no} | Non-continuous numbering"
        )

        if missing:
            report.append(f"    Missing : {missing}")

        if extra:
            report.append(f"    Extra   : {extra}")

    # ------------------------------------
    # Last stop number
    # ------------------------------------

    if max(stops) != len(stops):

        invalid_last_stop += 1

        report.append(
            f"{train_no} | Last stop is {max(stops)} but route has {len(stops)} stations"
        )

# ==========================================================
# SAVE REPORT
# ==========================================================

summary = []

summary.append("=" * 70)
summary.append("STOP NUMBER VALIDATION REPORT")
summary.append("=" * 70)
summary.append("")

summary.append(f"Total Trains              : {len(trains)}")
summary.append(f"Total Records             : {len(timetable)}")
summary.append("")

summary.append(f"Missing Stop Numbers      : {missing_stop_number}")
summary.append(f"Duplicate Stop Numbers    : {duplicate_stop_numbers}")
summary.append(f"Invalid First Stop        : {invalid_first_stop}")
summary.append(f"Invalid Last Stop         : {invalid_last_stop}")
summary.append(f"Non Continuous Routes     : {non_continuous_routes}")

summary.append("")
summary.append("=" * 70)
summary.append("DETAILS")
summary.append("=" * 70)

summary.extend(report)

with open(REPORT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(summary))

# ==========================================================
# PRINT
# ==========================================================

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"Missing Stop Numbers   : {missing_stop_number}")
print(f"Duplicate Stop Numbers : {duplicate_stop_numbers}")
print(f"Invalid First Stop     : {invalid_first_stop}")
print(f"Invalid Last Stop      : {invalid_last_stop}")
print(f"Non Continuous Routes  : {non_continuous_routes}")

print()
print("Report Saved To:")
print(REPORT_FILE)

print()
print("=" * 70)
print("STOP NUMBER VALIDATION COMPLETED")
print("=" * 70)