import json
import os
from collections import OrderedDict

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

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "train_master.json"
)

# ==========================================================
# LOAD DATA
# ==========================================================

print("=" * 70)
print("CREATING TRAIN MASTER")
print("=" * 70)

with open(INPUT_FILE, "r", encoding="utf-8") as file:
    timetable = json.load(file)

print(f"Loaded Records : {len(timetable):,}")

# ==========================================================
# TRAIN TYPE DETECTION
# ==========================================================

def detect_train_type(train_name):

    if not train_name:
        return "Unknown"

    name = train_name.upper()

    if "VANDE BHARAT" in name:
        return "Vande Bharat"

    if "RAJDHANI" in name:
        return "Rajdhani"

    if "JAN SHATABDI" in name:
        return "Jan Shatabdi"

    if "SHATABDI" in name:
        return "Shatabdi"

    if "DURONTO" in name:
        return "Duronto"

    if "GARIB RATH" in name:
        return "Garib Rath"

    if "HAMSAFAR" in name:
        return "Humsafar"

    if "TEJAS" in name:
        return "Tejas"

    if "DOUBLE DECKER" in name:
        return "Double Decker"

    if "MEMU" in name:
        return "MEMU"

    if "DEMU" in name:
        return "DEMU"

    if "EMU" in name:
        return "EMU"

    if "LOCAL" in name:
        return "EMU"

    if "SUBURBAN" in name:
        return "EMU"

    if "PASSENGER" in name:
        return "Passenger"

    if "MAIL" in name:
        return "Mail"

    if "SUPERFAST" in name:
        return "Superfast"

    if " SF " in f" {name} ":
        return "Superfast"

    if "EXPRESS" in name:
        return "Express"

    if "EXP" in name:
        return "Express"

    return "Express"

# ==========================================================
# PRIORITY ASSIGNMENT
# Lower Number = Higher Priority
# ==========================================================

def assign_priority(train_type):

    priority_map = {

        "Vande Bharat": 1,
        "Rajdhani": 2,
        "Shatabdi": 3,
        "Duronto": 4,
        "Tejas": 5,
        "Garib Rath": 6,
        "Humsafar": 7,
        "Jan Shatabdi": 8,
        "Superfast": 9,
        "Mail": 10,
        "Express": 11,
        "MEMU": 12,
        "DEMU": 13,
        "Passenger": 14,
        "EMU": 15

    }

    return priority_map.get(train_type, 99)

# ==========================================================
# GROUP BY TRAIN
# ==========================================================

grouped = {}

for row in timetable:

    train_no = str(row.get("train_number", "")).strip()

    if train_no == "":
        continue

    grouped.setdefault(train_no, []).append(row)

# ==========================================================
# CREATE TRAIN MASTER
# ==========================================================

train_master = []

for train_no, rows in grouped.items():

    rows.sort(key=lambda x: x["stop_number"])

    train_name = rows[0]["train_name"].strip()

    train_type = detect_train_type(train_name)

    priority = assign_priority(train_type)

    train = OrderedDict()

    train["train_number"] = train_no
    train["train_name"] = train_name
    train["train_type"] = train_type
    train["priority"] = priority
    train["maximum_speed_kmph"] = None
    train["operator"] = "Indian Railways"
    train["zone"] = None
    train["source_station"] = rows[0]["station_code"]
    train["destination_station"] = rows[-1]["station_code"]

    train_master.append(train)

# ==========================================================
# SORT BY TRAIN NUMBER
# ==========================================================

train_master.sort(key=lambda x: x["train_number"])

# ==========================================================
# SAVE
# ==========================================================

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        train_master,
        file,
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

print(f"Total Trains : {len(train_master):,}")

print()

type_count = {}

for train in train_master:

    t = train["train_type"]

    type_count[t] = type_count.get(t, 0) + 1

print("Train Types")

for key in sorted(type_count):

    print(f"{key:<20} : {type_count[key]}")

print()

priority_count = {}

for train in train_master:

    p = train["priority"]

    priority_count[p] = priority_count.get(p, 0) + 1

print("Priority Distribution")

for p in sorted(priority_count):

    print(f"Priority {p:<2} : {priority_count[p]}")

print()

print("Saved To:")
print(OUTPUT_FILE)

print()
print("=" * 70)
print("TRAIN MASTER CREATED")
print("=" * 70)