import json
import os
from collections import defaultdict


# ==========================================================
# PATHS
# ==========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

TIMETABLE_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "project_timetable_ordered.json"
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
# LOAD
# ==========================================================

with open(TIMETABLE_FILE, "r", encoding="utf-8") as f:
    timetable = json.load(f)

with open(TRAIN_MASTER_FILE, "r", encoding="utf-8") as f:
    train_master = json.load(f)

with open(STATION_PROFILE_FILE, "r", encoding="utf-8") as f:
    station_profile = json.load(f)


# ==========================================================
# TRAIN LOOKUP
# ==========================================================

train_lookup = {
    str(train["train_number"]).strip(): train
    for train in train_master
}


# ==========================================================
# STATION LOOKUP
# ==========================================================

station_lookup = {
    station["station_code"]: station
    for station in station_profile
}


# ==========================================================
# FIND EMU / MEMU STATIONS
# ==========================================================

small_train_stations = defaultdict(set)

for record in timetable:

    train_number = str(
        record["train_number"]
    ).strip()

    train = train_lookup.get(train_number)

    if not train:
        continue

    train_type = str(
        train.get("train_type", "")
    ).upper()

    if train_type in {"EMU", "MEMU"}:

        small_train_stations[
            record["station_code"]
        ].add(train_type)


# ==========================================================
# REPORT
# ==========================================================

print("=" * 70)
print("SUBURBAN PLATFORM DIAGNOSTIC")
print("=" * 70)

print(
    f"\nEMU/MEMU stations : "
    f"{len(small_train_stations)}"
)

print()

for station_code in sorted(
    small_train_stations
):

    station = station_lookup.get(
        station_code
    )

    print("=" * 70)
    print(
        f"STATION : {station_code}"
    )

    print(
        f"TRAIN TYPES : "
        f"{', '.join(sorted(small_train_stations[station_code]))}"
    )

    if not station:

        print(
            "ERROR: Station not found "
            "in station profile."
        )

        continue

    platforms = station.get(
        "platforms",
        []
    )

    mainline = []
    suburban = []
    unknown = []

    for platform in platforms:

        number = platform.get(
            "platform_number"
        )

        platform_type = str(
            platform.get(
                "platform_type",
                ""
            )
        ).upper()

        if platform_type == "MAINLINE":

            mainline.append(number)

        elif platform_type == "SUBURBAN":

            suburban.append(number)

        else:

            unknown.append(
                (
                    number,
                    platform_type
                )
            )

    print(
        f"MAINLINE platforms : "
        f"{mainline}"
    )

    print(
        f"SUBURBAN platforms : "
        f"{suburban}"
    )

    if unknown:

        print(
            f"UNKNOWN platforms  : "
            f"{unknown}"
        )


# ==========================================================
# FINAL SUMMARY
# ==========================================================

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)

stations_with_suburban = 0
stations_without_suburban = 0

for station_code in small_train_stations:

    station = station_lookup.get(
        station_code
    )

    if not station:
        continue

    platforms = station.get(
        "platforms",
        []
    )

    has_suburban = any(
        str(
            p.get(
                "platform_type",
                ""
            )
        ).upper() == "SUBURBAN"
        for p in platforms
    )

    if has_suburban:

        stations_with_suburban += 1

    else:

        stations_without_suburban += 1


print(
    f"EMU/MEMU stations with "
    f"SUBURBAN platform : "
    f"{stations_with_suburban}"
)

print(
    f"EMU/MEMU stations without "
    f"SUBURBAN platform : "
    f"{stations_without_suburban}"
)

print()
print("NO FILES WERE MODIFIED.")