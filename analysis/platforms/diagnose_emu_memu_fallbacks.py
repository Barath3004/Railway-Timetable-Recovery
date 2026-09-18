import json
import os
from collections import defaultdict

# ==========================================================
# PATHS
# ==========================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TIMETABLE_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "project_timetable_platform_working.json"
)

TRAIN_MASTER_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "train_master.json"
)

STATION_PROFILE_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "station",
    "station_platform_profile.json"
)

# ==========================================================
# LOAD FILES
# ==========================================================

print("=" * 70)
print("DIAGNOSE EMU/MEMU MAINLINE FALLBACKS")
print("=" * 70)

with open(TIMETABLE_FILE, "r", encoding="utf-8") as file:
    timetable = json.load(file)

with open(TRAIN_MASTER_FILE, "r", encoding="utf-8") as file:
    train_master = json.load(file)

with open(STATION_PROFILE_FILE, "r", encoding="utf-8") as file:
    station_profile = json.load(file)

# ==========================================================
# LOOKUPS
# ==========================================================

train_lookup = {
    str(train["train_number"]): train
    for train in train_master
}

station_lookup = {
    station["station_code"]: station
    for station in station_profile
}

# ==========================================================
# FIND EMU/MEMU MAINLINE RECORDS
# ==========================================================

fallbacks = []

for row in timetable:

    train_no = str(row.get("train_number"))

    train = train_lookup.get(train_no)

    if not train:
        continue

    train_type = str(
        train.get("train_type", "")
    ).upper()

    platform_type = str(
        row.get("platform_type", "")
    ).upper()

    if train_type in ["EMU", "MEMU"] and platform_type == "MAINLINE":

        fallbacks.append({
            "train_number": train_no,
            "train_name": train.get("train_name"),
            "train_type": train_type,
            "station_code": row.get("station_code"),
            "station_name": row.get("station_name"),
            "arrival": row.get("arrival"),
            "departure": row.get("departure"),
            "platform_number": row.get("platform_number"),
            "platform_type": platform_type,
        })

# ==========================================================
# SUMMARY
# ==========================================================

print()
print(
    f"EMU/MEMU MAINLINE FALLBACK RECORDS : {len(fallbacks)}"
)

stations = sorted(
    {
        row["station_code"]
        for row in fallbacks
    }
)

print(
    f"Stations With Fallbacks            : {len(stations)}"
)

# ==========================================================
# NO FALLBACKS
# ==========================================================

if not fallbacks:

    print()
    print("NO EMU/MEMU MAINLINE FALLBACKS FOUND.")
    print()
    print("=" * 70)
    print("DIAGNOSTIC COMPLETED")
    print("=" * 70)

    raise SystemExit

# ==========================================================
# GROUP BY STATION
# ==========================================================

by_station = defaultdict(list)

for row in fallbacks:

    by_station[row["station_code"]].append(row)

# ==========================================================
# DISPLAY
# ==========================================================

for station_code in sorted(by_station):

    station = station_lookup.get(
        station_code,
        {}
    )

    station_name = station.get(
        "station_name",
        by_station[station_code][0]["station_name"]
    )

    platforms = station.get(
        "platforms",
        []
    )

    mainline_platforms = []

    suburban_platforms = []

    for platform in platforms:

        number = platform.get("platform_number")
        ptype = str(
            platform.get("platform_type", "")
        ).upper()

        if ptype == "MAINLINE":
            mainline_platforms.append(number)

        elif ptype == "SUBURBAN":
            suburban_platforms.append(number)

    print()
    print("-" * 70)

    print(f"STATION : {station_code}")
    print(f"NAME    : {station_name}")

    print(
        f"MAINLINE PLATFORMS : "
        f"{sorted(mainline_platforms)}"
    )

    print(
        f"SUBURBAN PLATFORMS : "
        f"{sorted(suburban_platforms)}"
    )

    print()

    for row in sorted(
        by_station[station_code],
        key=lambda x: (
            str(x.get("arrival")),
            str(x.get("train_number"))
        )
    ):

        print(
            f"{row['train_number']} | "
            f"{row['train_name']} | "
            f"{row['train_type']} | "
            f"{row['arrival']} - "
            f"{row['departure']} | "
            f"Platform {row['platform_number']} | "
            f"{row['platform_type']}"
        )

# ==========================================================
# STATION CATEGORY SUMMARY
# ==========================================================

print()
print("=" * 70)
print("FALLBACK CATEGORY SUMMARY")
print("=" * 70)

with_suburban = 0
without_suburban = 0

for station_code, rows in by_station.items():

    station = station_lookup.get(
        station_code,
        {}
    )

    platforms = station.get(
        "platforms",
        []
    )

    has_suburban = any(
        str(p.get("platform_type", "")).upper()
        == "SUBURBAN"
        for p in platforms
    )

    if has_suburban:
        with_suburban += len(rows)
    else:
        without_suburban += len(rows)

print(
    f"Fallbacks at stations WITH SUBURBAN platforms    : "
    f"{with_suburban}"
)

print(
    f"Fallbacks at stations WITHOUT SUBURBAN platforms : "
    f"{without_suburban}"
)

# ==========================================================
# TRAIN SUMMARY
# ==========================================================

print()
print("=" * 70)
print("TRAIN TYPE SUMMARY")
print("=" * 70)

type_counts = defaultdict(int)

for row in fallbacks:

    type_counts[row["train_type"]] += 1

for train_type in sorted(type_counts):

    print(
        f"{train_type:<10} : "
        f"{type_counts[train_type]:,}"
    )

# ==========================================================
# END
# ==========================================================

print()
print("=" * 70)
print("DIAGNOSTIC COMPLETED")
print("=" * 70)