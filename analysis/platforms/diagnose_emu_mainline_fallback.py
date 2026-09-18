import json
import os
from collections import defaultdict

# ==========================================================
# PATHS
# ==========================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FINAL_TIMETABLE_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "project_timetable",
    "project_timetable_platform.json"
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

with open(
    FINAL_TIMETABLE_FILE,
    "r",
    encoding="utf-8"
) as file:

    timetable = json.load(file)


with open(
    TRAIN_MASTER_FILE,
    "r",
    encoding="utf-8"
) as file:

    train_master = json.load(file)


with open(
    STATION_PROFILE_FILE,
    "r",
    encoding="utf-8"
) as file:

    station_profile = json.load(file)


# ==========================================================
# TRAIN LOOKUP
# ==========================================================

train_lookup = {}

for train in train_master:

    train_number = str(
        train.get("train_number")
    )

    train_lookup[train_number] = train


# ==========================================================
# STATION LOOKUP
# ==========================================================

station_lookup = {}

for station in station_profile:

    station_code = station.get(
        "station_code"
    )

    station_lookup[station_code] = station


# ==========================================================
# FIND EMU/MEMU MAINLINE RECORDS
# ==========================================================

fallback_records = []

for record in timetable:

    train_number = str(
        record.get("train_number")
    )

    train = train_lookup.get(
        train_number
    )

    if train is None:
        continue

    train_type = str(
        train.get("train_type", "")
    ).upper()

    if train_type not in {
        "EMU",
        "MEMU"
    }:
        continue

    if record.get("platform_type") != "MAINLINE":
        continue

    fallback_records.append(
        {
            "train_number": train_number,
            "train_name": train.get("train_name"),
            "train_type": train_type,
            "station_code": record.get("station_code"),
            "station_name": record.get("station_name"),
            "platform_number": record.get("platform_number"),
            "platform_type": record.get("platform_type"),
            "arrival": record.get("arrival"),
            "departure": record.get("departure"),
            "day": record.get("day"),
            "stop_number": record.get("stop_number"),
        }
    )


# ==========================================================
# GROUP BY STATION
# ==========================================================

station_fallbacks = defaultdict(list)

for record in fallback_records:

    station_fallbacks[
        record["station_code"]
    ].append(record)


# ==========================================================
# SUMMARY
# ==========================================================

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)

print(
    f"\nEMU/MEMU MAINLINE FALLBACK RECORDS : "
    f"{len(fallback_records)}"
)

print(
    f"Stations With Fallbacks            : "
    f"{len(station_fallbacks)}"
)


# ==========================================================
# STATION-BY-STATION ANALYSIS
# ==========================================================

print()
print("=" * 70)
print("STATION ANALYSIS")
print("=" * 70)


for station_code in sorted(station_fallbacks):

    station = station_lookup.get(
        station_code
    )

    print()
    print("-" * 70)

    if station is None:

        print(
            f"STATION : {station_code}"
        )

        print(
            "WARNING : Station not found in profile"
        )

    else:

        print(
            f"STATION : {station_code}"
        )

        print(
            f"NAME    : "
            f"{station.get('station_name')}"
        )

        platforms = station.get(
            "platforms",
            []
        )

        mainline_platforms = []
        suburban_platforms = []

        for platform in platforms:

            number = platform.get(
                "platform_number"
            )

            platform_type = platform.get(
                "platform_type"
            )

            if platform_type == "MAINLINE":

                mainline_platforms.append(
                    number
                )

            elif platform_type == "SUBURBAN":

                suburban_platforms.append(
                    number
                )

        print(
            f"MAINLINE PLATFORMS : "
            f"{mainline_platforms}"
        )

        print(
            f"SUBURBAN PLATFORMS : "
            f"{suburban_platforms}"
        )

    print()

    for record in station_fallbacks[
        station_code
    ]:

        print(
            f"{record['train_number']} | "
            f"{record['train_name']} | "
            f"{record['train_type']} | "
            f"{record['arrival']} - "
            f"{record['departure']} | "
            f"Platform {record['platform_number']} | "
            f"{record['platform_type']}"
        )


# ==========================================================
# CHECK WHETHER SUBURBAN PLATFORM EXISTS
# ==========================================================

print()
print("=" * 70)
print("FALLBACK CLASSIFICATION")
print("=" * 70)

stations_without_suburban = []
stations_with_suburban = []

for station_code in sorted(station_fallbacks):

    station = station_lookup.get(
        station_code
    )

    suburban_exists = False

    if station:

        for platform in station.get(
            "platforms",
            []
        ):

            if platform.get(
                "platform_type"
            ) == "SUBURBAN":

                suburban_exists = True
                break

    if suburban_exists:

        stations_with_suburban.append(
            station_code
        )

    else:

        stations_without_suburban.append(
            station_code
        )


print(
    "\nFallbacks at stations WITHOUT "
    "SUBURBAN platforms:"
)

if stations_without_suburban:

    for station in stations_without_suburban:

        count = len(
            station_fallbacks[station]
        )

        print(
            f"  {station:<6} : {count} records"
        )

else:

    print("  None")


print(
    "\nFallbacks at stations WITH "
    "SUBURBAN platforms:"
)

if stations_with_suburban:

    for station in stations_with_suburban:

        count = len(
            station_fallbacks[station]
        )

        print(
            f"  {station:<6} : {count} records"
        )

else:

    print("  None")


# ==========================================================
# FINAL DIAGNOSIS
# ==========================================================

print()
print("=" * 70)
print("FINAL DIAGNOSIS")
print("=" * 70)

if stations_with_suburban:

    print(
        "\nWARNING:"
    )

    print(
        "Some EMU/MEMU records are using MAINLINE"
        " platforms at stations that have SUBURBAN"
        " platforms."
    )

    print(
        "\nThese records require further investigation."
    )

else:

    print(
        "\nRESULT:"
    )

    print(
        "All EMU/MEMU MAINLINE allocations occur at"
        " stations without SUBURBAN platforms."
    )

    print(
        "\nThe fallback behavior is consistent with"
        " the platform availability rules."
    )


print()
print("=" * 70)
print("DIAGNOSTIC COMPLETED")
print("=" * 70)