import json
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TIMETABLE_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "project_timetable"
    / "project_timetable_platform.json"
)

PLATFORM_PROFILE_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "station"
    / "station_platform_profile.json"
)


# ============================================================
# PROJECT STATIONS
# ============================================================

PROJECT_STATIONS = {
    "MAS",
    "MS",
    "BBQ",
    "PER",
    "VLK",
    "ABU",
    "AVD",
    "TRL",
    "AJJ",
    "KPD",
    "JTJ",
    "TBM",
    "CGL",
    "TMV",
    "VM",
    "VRI",
    "CUPJ",
    "TPJ",
    "KRR",
    "DG",
    "MDU",
    "VPT",
    "SVKS",
    "CVP",
    "TEN",
    "NCJ",
    "RMD",
    "CAPE",
    "ERL",
    "PASA",
    "NYY",
    "TVC",
    "TVP",
    "VAK",
    "QLN",
    "KYJ",
}


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("VALIDATE FINAL PROJECT TIMETABLE")
print("=" * 70)

with open(TIMETABLE_FILE, "r", encoding="utf-8") as f:
    timetable = json.load(f)

with open(PLATFORM_PROFILE_FILE, "r", encoding="utf-8") as f:
    platform_profile = json.load(f)

print(f"\nTimetable Records : {len(timetable)}")


# ============================================================
# BUILD PLATFORM LOOKUP
# ============================================================

platform_lookup = defaultdict(dict)

for station in platform_profile:

    station_code = station.get("station_code")

    platforms = station.get("platforms", [])

    for platform in platforms:

        platform_number = platform.get("platform_number")
        platform_type = platform.get("platform_type")

        if platform_number is not None:

            platform_lookup[station_code][
                str(platform_number)
            ] = platform_type


# ============================================================
# VALIDATION CONTAINERS
# ============================================================

invalid_station = []
missing_fields = []
invalid_platform_number = []
invalid_platform_type = []
platform_not_in_profile = []
platform_type_mismatch = []
duplicate_records = []
invalid_time = []
invalid_stop_order = []


# ============================================================
# REQUIRED FIELDS
# ============================================================

required_fields = [
    "arrival",
    "day",
    "train_name",
    "station_name",
    "station_code",
    "id",
    "train_number",
    "departure",
    "stop_number",
    "platform_number",
    "platform_type",
    "platform_allocated_by",
]


# ============================================================
# BASIC RECORD VALIDATION
# ============================================================

seen_ids = set()

for index, record in enumerate(timetable):

    # --------------------------------------------------------
    # REQUIRED FIELDS
    # --------------------------------------------------------

    missing = [
        field
        for field in required_fields
        if field not in record
    ]

    if missing:

        missing_fields.append(
            {
                "index": index,
                "missing": missing,
            }
        )

    # --------------------------------------------------------
    # STATION VALIDATION
    # --------------------------------------------------------

    station_code = record.get("station_code")

    if station_code not in PROJECT_STATIONS:

        invalid_station.append(
            {
                "index": index,
                "station_code": station_code,
            }
        )

    # --------------------------------------------------------
    # DUPLICATE RECORD ID
    # --------------------------------------------------------

    record_id = record.get("id")

    if record_id in seen_ids:

        duplicate_records.append(
            {
                "index": index,
                "id": record_id,
            }
        )

    else:

        seen_ids.add(record_id)

    # --------------------------------------------------------
    # PLATFORM NUMBER
    # --------------------------------------------------------

    platform_number = record.get("platform_number")

    if platform_number is None:

        invalid_platform_number.append(
            {
                "index": index,
                "station_code": station_code,
            }
        )

    else:

        try:

            int(platform_number)

        except (ValueError, TypeError):

            invalid_platform_number.append(
                {
                    "index": index,
                    "station_code": station_code,
                    "platform": platform_number,
                }
            )

    # --------------------------------------------------------
    # PLATFORM TYPE
    # --------------------------------------------------------

    platform_type = record.get("platform_type")

    if platform_type not in {
        "MAINLINE",
        "SUBURBAN",
    }:

        invalid_platform_type.append(
            {
                "index": index,
                "station_code": station_code,
                "platform_type": platform_type,
            }
        )

    # --------------------------------------------------------
    # PLATFORM EXISTS IN PROFILE
    # --------------------------------------------------------

    if station_code in platform_lookup:

        platform_key = str(platform_number)

        if platform_key not in platform_lookup[station_code]:

            platform_not_in_profile.append(
                {
                    "index": index,
                    "station_code": station_code,
                    "platform": platform_number,
                }
            )

        else:

            expected_type = platform_lookup[
                station_code
            ][platform_key]

            if platform_type != expected_type:

                platform_type_mismatch.append(
                    {
                        "index": index,
                        "station_code": station_code,
                        "platform": platform_number,
                        "record_type": platform_type,
                        "profile_type": expected_type,
                    }
                )

    else:

        platform_not_in_profile.append(
            {
                "index": index,
                "station_code": station_code,
                "platform": platform_number,
            }
        )

    # --------------------------------------------------------
    # TIME VALIDATION
    # --------------------------------------------------------

    for field in ["arrival", "departure"]:

        value = record.get(field)

        if value in {None, "", "None"}:
            continue

        try:

            datetime.strptime(
                str(value),
                "%H:%M:%S",
            )

        except ValueError:

            invalid_time.append(
                {
                    "index": index,
                    "field": field,
                    "value": value,
                }
            )


# ============================================================
# TRAIN STOP ORDER VALIDATION
# ============================================================

train_records = defaultdict(list)

for record in timetable:

    train_key = (
        record.get("train_number"),
        record.get("day"),
    )

    train_records[train_key].append(record)


for train_key, records in train_records.items():

    # Sort by original timetable stop number.
    records_sorted = sorted(
        records,
        key=lambda x: x.get("stop_number", 0),
    )

    stop_numbers = [
        record.get("stop_number")
        for record in records_sorted
    ]

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Stop numbers do NOT have to be consecutive.
    #
    # Example:
    #
    # Original train route:
    # 1 MAS
    # 2 VJM
    # 3 PER
    # 4 ...
    # 5 AJJ
    #
    # After filtering the project stations:
    #
    # 1 MAS
    # 3 PER
    # 5 AJJ
    #
    # This is VALID.
    #
    # We only need to make sure the original stop numbers
    # remain strictly increasing.
    # --------------------------------------------------------

    for i in range(1, len(stop_numbers)):

        previous_stop = stop_numbers[i - 1]
        current_stop = stop_numbers[i]

        try:

            if current_stop <= previous_stop:

                invalid_stop_order.append(
                    {
                        "train": train_key,
                        "stop_numbers": stop_numbers,
                    }
                )

                break

        except TypeError:

            invalid_stop_order.append(
                {
                    "train": train_key,
                    "stop_numbers": stop_numbers,
                }
            )

            break


# ============================================================
# STATION STATISTICS
# ============================================================

station_counts = Counter(
    record.get("station_code")
    for record in timetable
)


# ============================================================
# PLATFORM STATISTICS
# ============================================================

platform_counts = Counter(
    (
        record.get("station_code"),
        record.get("platform_number"),
    )
    for record in timetable
)


# ============================================================
# TRAIN STATISTICS
# ============================================================

unique_trains = len(
    {
        (
            record.get("train_number"),
            record.get("day"),
        )
        for record in timetable
    }
)


# ============================================================
# VALIDATION REPORT
# ============================================================

print("\n")
print("=" * 70)
print("VALIDATION RESULTS")
print("=" * 70)

print(
    f"\nTotal Records              : {len(timetable)}"
)

print(
    f"Unique Train-Day Groups    : {unique_trains}"
)

print(
    f"Stations Represented       : {len(station_counts)}"
)


# ============================================================
# DATA QUALITY
# ============================================================

print("\n")
print("DATA QUALITY")
print("-" * 70)

print(
    f"Missing Required Fields    : {len(missing_fields)}"
)

print(
    f"Invalid Station Codes      : {len(invalid_station)}"
)

print(
    f"Duplicate Record IDs       : {len(duplicate_records)}"
)

print(
    f"Invalid Platform Numbers   : {len(invalid_platform_number)}"
)

print(
    f"Invalid Platform Types     : {len(invalid_platform_type)}"
)

print(
    f"Platform Not In Profile    : {len(platform_not_in_profile)}"
)

print(
    f"Platform Type Mismatch     : {len(platform_type_mismatch)}"
)

print(
    f"Invalid Time Values        : {len(invalid_time)}"
)

print(
    f"Invalid Stop Ordering      : {len(invalid_stop_order)}"
)


# ============================================================
# PLATFORM SUMMARY
# ============================================================

print("\n")
print("=" * 70)
print("PLATFORM SUMMARY")
print("=" * 70)

mainline_count = sum(
    1
    for record in timetable
    if record.get("platform_type") == "MAINLINE"
)

suburban_count = sum(
    1
    for record in timetable
    if record.get("platform_type") == "SUBURBAN"
)

print(
    f"MAINLINE Records           : {mainline_count}"
)

print(
    f"SUBURBAN Records           : {suburban_count}"
)


# ============================================================
# STATION SUMMARY
# ============================================================

print("\n")
print("=" * 70)
print("STATION RECORD COUNTS")
print("=" * 70)

for station_code in sorted(station_counts):

    print(
        f"{station_code:<6} : "
        f"{station_counts[station_code]}"
    )


# ============================================================
# UNUSED PROJECT STATIONS
# ============================================================

unused_stations = (
    PROJECT_STATIONS
    - set(station_counts.keys())
)

print("\n")
print("=" * 70)
print("PROJECT STATIONS NOT REPRESENTED")
print("=" * 70)

if unused_stations:

    for station in sorted(unused_stations):

        print(station)

else:

    print("None")


# ============================================================
# FINAL STATUS
# ============================================================

total_errors = (
    len(missing_fields)
    + len(invalid_station)
    + len(duplicate_records)
    + len(invalid_platform_number)
    + len(invalid_platform_type)
    + len(platform_not_in_profile)
    + len(platform_type_mismatch)
    + len(invalid_time)
    + len(invalid_stop_order)
)


print("\n")
print("=" * 70)
print("FINAL VALIDATION STATUS")
print("=" * 70)

if total_errors == 0:

    print("\nSTATUS : PASS")

    print(
        "\nThe final project timetable is structurally valid."
    )

else:

    print("\nSTATUS : FAIL")

    print(
        f"\nTotal validation errors : {total_errors}"
    )