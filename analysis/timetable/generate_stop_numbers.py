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

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "project_timetable_ordered.json"
)

# ==========================================================
# LOAD DATA
# ==========================================================

print("=" * 70)
print("GENERATING STOP NUMBERS")
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
# TIME CONVERTER
# ==========================================================

def time_to_minutes(value):

    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    if value.lower() == "none":
        return None

    if value in ["--", "NA", "N/A"]:
        return None

    try:

        parts = value.split(":")

        if len(parts) == 3:

            hour = int(parts[0])
            minute = int(parts[1])

        elif len(parts) == 2:

            hour = int(parts[0])
            minute = int(parts[1])

        else:

            return None

        return hour * 60 + minute

    except:

        return None


# ==========================================================
# SORT KEY
# ==========================================================

def sort_key(row):

    arrival = row.get("arrival")
    departure = row.get("departure")

    arr = time_to_minutes(arrival)
    dep = time_to_minutes(departure)

    day = row.get("day")

    if day is None:

        day = 1

    # --------------------------
    # Source station
    # --------------------------

    if arrival in [None, "", "None"]:

        return (
            0,
            int(day),
            dep if dep is not None else 9999
        )

    # --------------------------
    # Destination station
    # --------------------------

    if departure in [None, "", "None"]:

        return (
            2,
            int(day),
            arr if arr is not None else 9999
        )

    # --------------------------
    # Intermediate station
    # --------------------------

    time = dep

    if time is None:

        time = arr

    if time is None:

        time = 9999

    return (
        1,
        int(day),
        time
    )


# ==========================================================
# GENERATE STOP NUMBERS
# ==========================================================

ordered_dataset = []

for train_no, rows in trains.items():

    rows = sorted(rows, key=sort_key)

    stop = 1

    for row in rows:

        row["stop_number"] = stop

        ordered_dataset.append(row)

        stop += 1


# ==========================================================
# SAVE
# ==========================================================

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

    json.dump(
        ordered_dataset,
        f,
        indent=4,
        ensure_ascii=False
    )

# ==========================================================
# SUMMARY
# ==========================================================

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"Processed Trains : {len(trains):,}")
print(f"Processed Rows   : {len(ordered_dataset):,}")

print()
print("Saved File:")
print(OUTPUT_FILE)

print()
print("=" * 70)
print("STOP NUMBER GENERATION COMPLETED")
print("=" * 70)