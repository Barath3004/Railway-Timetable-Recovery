import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

STATION_PROFILE_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "station"
    / "station_platform_profile.json"
)

TRAIN_MASTER_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "train_master.json"
)

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "project_timetable_platform_working.json"
)

print("=" * 70)
print("DEBUG VLK EMU PLATFORM ALLOCATION")
print("=" * 70)

# ----------------------------------------------------------
# LOAD
# ----------------------------------------------------------

with open(STATION_PROFILE_FILE, "r", encoding="utf-8") as f:
    stations = json.load(f)

with open(TRAIN_MASTER_FILE, "r", encoding="utf-8") as f:
    train_master = json.load(f)

with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
    timetable = json.load(f)

# ----------------------------------------------------------
# VLK PROFILE
# ----------------------------------------------------------

vlk = next(
    (
        station
        for station in stations
        if station.get("station_code") == "VLK"
    ),
    None
)

print("\nVLK STATION PROFILE")
print("-" * 70)

if vlk is None:

    print("VLK NOT FOUND IN STATION PROFILE")

else:

    print("Station Code :", vlk.get("station_code"))
    print("Station Name :", vlk.get("station_name"))

    print("\nPlatforms:")

    for platform in vlk.get("platforms", []):

        print(
            f"Platform {platform.get('platform_number')}"
            f" -> {platform.get('platform_type')}"
        )

# ----------------------------------------------------------
# TRAIN MASTER
# ----------------------------------------------------------

print("\n")
print("TRAIN MASTER")
print("-" * 70)

target_trains = {"43501", "43506"}

for train in train_master:

    if str(train.get("train_number")) in target_trains:

        print(
            train.get("train_number"),
            "|",
            train.get("train_name"),
            "|",
            train.get("train_type")
        )

# ----------------------------------------------------------
# GENERATED ALLOCATION
# ----------------------------------------------------------

print("\n")
print("GENERATED ALLOCATION")
print("-" * 70)

for row in timetable:

    if (
        row.get("station_code") == "VLK"
        and str(row.get("train_number")) in target_trains
    ):

        print(
            row.get("train_number"),
            "|",
            row.get("train_name"),
            "|",
            "Platform",
            row.get("platform_number"),
            "|",
            row.get("platform_type"),
            "|",
            "Allocated By:",
            row.get("platform_allocated_by")
        )

print("\n")
print("=" * 70)
print("DEBUG COMPLETED")
print("=" * 70)