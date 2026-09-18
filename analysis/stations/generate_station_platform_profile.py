import os
import json
import pandas as pd

# ==========================================================
# PATHS
# ==========================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "station",
    "station_reference.csv"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "station",
    "station_platform_profile.json"
)

# ==========================================================
# LOAD DATA
# ==========================================================

print("=" * 70)
print("GENERATING STATION PLATFORM PROFILE")
print("=" * 70)

stations = pd.read_csv(INPUT_FILE)

print(f"Loaded Stations : {len(stations)}")

# ==========================================================
# BUFFER RULE
# ==========================================================

def get_station_buffer(platforms):

    if platforms <= 4:
        return 5

    elif platforms <= 8:
        return 10

    elif platforms <= 12:
        return 15

    elif platforms <= 16:
        return 20

    return 25

# ==========================================================
# PLATFORM SPLIT
# ==========================================================

def get_platform_split(total):

    if total <= 3:
        suburban = 0

    elif total == 4:
        suburban = 1

    elif total <= 8:
        suburban = 1

    elif total <= 10:
        suburban = 2

    elif total <= 12:
        suburban = 3

    elif total <= 14:
        suburban = 4

    elif total <= 16:
        suburban = 5

    else:
        suburban = 6

    mainline = total - suburban

    return mainline, suburban

# ==========================================================
# BUILD PROFILE
# ==========================================================

profile = []

for _, row in stations.iterrows():

    total = int(row["platforms_total"])

    mainline, suburban = get_platform_split(total)

    station = {
        "station_code": row["station_code"],
        "station_name": row["station_name"],
        "platforms_total": total,
        "station_buffer_minutes": get_station_buffer(total),
        "platforms": []
    }

    # MAINLINE Platforms

    for i in range(1, mainline + 1):

        station["platforms"].append({

            "platform_number": i,

            "platform_type": "MAINLINE"

        })

    # SUBURBAN Platforms

    for i in range(mainline + 1, total + 1):

        station["platforms"].append({

            "platform_number": i,

            "platform_type": "SUBURBAN"

        })

    profile.append(station)

# ==========================================================
# SAVE
# ==========================================================

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        profile,
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

print(f"Stations Processed : {len(profile)}")

mainline_total = 0
suburban_total = 0

for station in profile:

    for platform in station["platforms"]:

        if platform["platform_type"] == "MAINLINE":
            mainline_total += 1
        else:
            suburban_total += 1

print(f"Total MAINLINE Platforms : {mainline_total}")
print(f"Total SUBURBAN Platforms : {suburban_total}")

print()
print("Saved To:")
print(OUTPUT_FILE)

print()
print("=" * 70)
print("STATION PLATFORM PROFILE GENERATED")
print("=" * 70)