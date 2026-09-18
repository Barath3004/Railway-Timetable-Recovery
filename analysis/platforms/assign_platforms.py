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

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "project_timetable_platform.json"
)


# ==========================================================
# BUFFER CONFIGURATION
# ==========================================================

# EMU / MEMU / Local-style trains
SMALL_TRAIN_BUFFER_MINUTES = 5

# Mainline trains use the station-defined buffer.


# ==========================================================
# CONSTANTS
# ==========================================================

MINUTES_PER_DAY = 24 * 60


print("=" * 70)
print("PLATFORM ALLOCATION ENGINE")
print("=" * 70)


# ==========================================================
# LOAD FILES
# ==========================================================

with open(
    TIMETABLE_FILE,
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


print(
    f"Timetable Records : {len(timetable):,}"
)

print(
    f"Train Master      : {len(train_master):,}"
)

print(
    f"Stations          : {len(station_profile):,}"
)


# ==========================================================
# BUILD TRAIN LOOKUP
# ==========================================================

train_lookup = {}

for train in train_master:

    train_number = str(
        train.get("train_number", "")
    ).strip()

    if train_number:

        train_lookup[
            train_number
        ] = train


# ==========================================================
# BUILD STATION LOOKUP
# ==========================================================

station_lookup = {}

for station in station_profile:

    station_code = str(
        station.get("station_code", "")
    ).strip().upper()

    if station_code:

        station_lookup[
            station_code
        ] = station


# ==========================================================
# TIME UTILITIES
# ==========================================================

def time_to_minutes(value):

    if value is None:
        return None

    value = str(value).strip()

    if value in [
        "",
        "--",
        "None",
        "null"
    ]:

        return None

    try:

        parts = value.split(":")

        hour = int(parts[0])
        minute = int(parts[1])

        return (
            hour * 60
            + minute
        )

    except Exception:

        return None


# ==========================================================
# DAY UTILITIES
# ==========================================================

def get_day(record):

    try:

        return int(
            record.get("day", 1)
        )

    except Exception:

        return 1


def absolute_time(day, minutes):

    return (
        (day - 1) * MINUTES_PER_DAY
        + minutes
    )


# ==========================================================
# TRAIN TYPE
# ==========================================================

def get_train_type(train_number):

    train_number = str(
        train_number
    ).strip()

    train = train_lookup.get(
        train_number
    )

    if train is None:

        return "Express"

    return str(
        train.get(
            "train_type",
            "Express"
        )
    ).strip()


# ==========================================================
# SMALL TRAIN CHECK
# ==========================================================

def is_small_train(train_type):

    train_type = str(
        train_type
    ).strip().upper()

    return train_type in {
        "EMU",
        "MEMU"
    }


# ==========================================================
# PLATFORM PREFERENCE
# ==========================================================

def preferred_platform_type(train_type):

    if is_small_train(train_type):

        return "SUBURBAN"

    return "MAINLINE"


# ==========================================================
# GROUP TIMETABLE BY STATION
# ==========================================================

station_records = defaultdict(list)

for row in timetable:

    station_code = str(
        row.get(
            "station_code",
            ""
        )
    ).strip().upper()

    station_records[
        station_code
    ].append(row)


print()

print(
    f"Stations With Train Stops : "
    f"{len(station_records)}"
)


# ==========================================================
# SORT STATION RECORDS
# ==========================================================

def station_sort_key(record):

    day = get_day(record)

    arrival = time_to_minutes(
        record.get("arrival")
    )

    departure = time_to_minutes(
        record.get("departure")
    )

    if arrival is None:

        arrival = departure

    if arrival is None:

        arrival = 99999

    try:

        stop_number = int(
            record.get(
                "stop_number",
                9999
            )
        )

    except Exception:

        stop_number = 9999

    return (
        day,
        arrival,
        stop_number
    )


for station_code in station_records:

    station_records[
        station_code
    ].sort(
        key=station_sort_key
    )


print(
    "Station Timetables Sorted."
)


# ==========================================================
# PLATFORM ALLOCATION
# ==========================================================

assigned_records = []

allocation_count = 0
fallback_count = 0
unassigned_count = 0

small_train_records = 0
small_train_suburban = 0
small_train_mainline_fallback = 0

mainline_records = 0
suburban_records = 0


print()
print("=" * 70)
print("ALLOCATING PLATFORMS")
print("=" * 70)


# ==========================================================
# PROCESS EACH STATION
# ==========================================================

for station_code, records in station_records.items():

    # ------------------------------------------------------
    # STATION NOT IN PROFILE
    # ------------------------------------------------------

    if station_code not in station_lookup:

        # No platform profile exists for this station.
        # Platform allocation cannot be performed.

        unassigned_count += len(records)

        continue


    station = station_lookup[
        station_code
    ]


    # ------------------------------------------------------
    # STATION BUFFER
    # ------------------------------------------------------

    station_buffer = station.get(
        "station_buffer_minutes",
        10
    )

    try:

        station_buffer = int(
            station_buffer
        )

    except Exception:

        station_buffer = 10


    # ------------------------------------------------------
    # PLATFORM LIST
    # ------------------------------------------------------

    platforms = station.get(
        "platforms",
        []
    )

    platform_types = {}


    for platform in platforms:

        try:

            number = int(
                platform[
                    "platform_number"
                ]
            )

        except Exception:

            continue


        platform_type = str(
            platform.get(
                "platform_type",
                "MAINLINE"
            )
        ).strip().upper()


        platform_types[
            number
        ] = platform_type


    # ------------------------------------------------------
    # PLATFORM AVAILABILITY
    #
    # Stores the absolute time when each platform becomes
    # available again.
    # ------------------------------------------------------

    platform_status = {}

    for platform_number in platform_types:

        platform_status[
            platform_number
        ] = 0


    # ======================================================
    # PROCESS TRAIN STOPS
    # ======================================================

    for row in records:

        train_number = str(
            row.get(
                "train_number",
                ""
            )
        ).strip()


        # --------------------------------------------------
        # DAY
        # --------------------------------------------------

        day = get_day(row)


        # --------------------------------------------------
        # ARRIVAL / DEPARTURE
        # --------------------------------------------------

        arrival = time_to_minutes(
            row.get("arrival")
        )

        departure = time_to_minutes(
            row.get("departure")
        )


        if arrival is None:

            arrival = departure


        if departure is None:

            departure = arrival


        # --------------------------------------------------
        # CANNOT ALLOCATE WITHOUT TIME
        # --------------------------------------------------

        if arrival is None:

            row["platform_number"] = None
            row["platform_type"] = None
            row["platform_allocated_by"] = "UNASSIGNED"

            assigned_records.append(row)

            unassigned_count += 1

            continue


        # --------------------------------------------------
        # OVERNIGHT HANDLING
        # --------------------------------------------------

        if departure < arrival:

            departure += MINUTES_PER_DAY


        # --------------------------------------------------
        # ABSOLUTE TIMELINE
        # --------------------------------------------------

        arrival_absolute = absolute_time(
            day,
            arrival
        )

        departure_absolute = absolute_time(
            day,
            departure
        )


        # --------------------------------------------------
        # TRAIN TYPE
        # --------------------------------------------------

        train_type = get_train_type(
            train_number
        )

        small_train = is_small_train(
            train_type
        )


        if small_train:

            small_train_records += 1


        # --------------------------------------------------
        # REQUIRED PLATFORM TYPE
        # --------------------------------------------------

        required_type = preferred_platform_type(
            train_type
        )


        # --------------------------------------------------
        # BUILD PLATFORM CANDIDATES
        # --------------------------------------------------

        preferred_platforms = []
        fallback_platforms = []


        for number, platform_type in platform_types.items():

            if platform_type == required_type:

                preferred_platforms.append(
                    number
                )

            else:

                fallback_platforms.append(
                    number
                )


        # --------------------------------------------------
        # SORT PLATFORM NUMBERS
        # --------------------------------------------------

        preferred_platforms.sort()
        fallback_platforms.sort()


        # ==================================================
        # ALLOCATION STRATEGY
        # ==================================================

        allocated = None
        allocated_type = None
        allocation_method = None


        # --------------------------------------------------
        # TRY PREFERRED PLATFORM
        # --------------------------------------------------

        for platform in preferred_platforms:

            available_time = platform_status.get(
                platform,
                0
            )


            if arrival_absolute >= available_time:

                allocated = platform

                allocated_type = platform_types[
                    platform
                ]

                allocation_method = "AUTO"

                break


        # --------------------------------------------------
        # TRY FALLBACK PLATFORM
        #
        # Only use fallback if it is actually free.
        # --------------------------------------------------

        if allocated is None:

            for platform in fallback_platforms:

                available_time = platform_status.get(
                    platform,
                    0
                )


                if arrival_absolute >= available_time:

                    allocated = platform

                    allocated_type = platform_types[
                        platform
                    ]

                    allocation_method = (
                        "AUTO_FALLBACK"
                    )

                    fallback_count += 1

                    break


        # --------------------------------------------------
        # NO PLATFORM AVAILABLE
        #
        # IMPORTANT:
        #
        # NEVER force a train onto an occupied platform.
        #
        # The train remains unassigned so that the later
        # recovery/optimization layer can handle it.
        # --------------------------------------------------

        if allocated is None:

            row["platform_number"] = None
            row["platform_type"] = None
            row["platform_allocated_by"] = "UNASSIGNED"

            assigned_records.append(row)

            unassigned_count += 1

            continue


        # ==================================================
        # BUFFER
        # ==================================================

        if small_train:

            buffer_minutes = (
                SMALL_TRAIN_BUFFER_MINUTES
            )

        else:

            buffer_minutes = (
                station_buffer
            )


        # ==================================================
        # UPDATE PLATFORM AVAILABILITY
        # ==================================================

        release_absolute = (
            departure_absolute
            + buffer_minutes
        )


        platform_status[
            allocated
        ] = release_absolute


        # ==================================================
        # SMALL TRAIN STATISTICS
        # ==================================================

        if small_train:

            if allocated_type == "SUBURBAN":

                small_train_suburban += 1

            else:

                small_train_mainline_fallback += 1


        # ==================================================
        # GENERAL PLATFORM STATISTICS
        # ==================================================

        if allocated_type == "MAINLINE":

            mainline_records += 1

        elif allocated_type == "SUBURBAN":

            suburban_records += 1


        # ==================================================
        # SAVE ALLOCATION
        # ==================================================

        row["platform_number"] = allocated

        row["platform_type"] = allocated_type

        row["platform_allocated_by"] = allocation_method

        assigned_records.append(row)

        allocation_count += 1


# ==========================================================
# SORT FINAL OUTPUT
# ==========================================================

assigned_records.sort(
    key=lambda row: (
        str(
            row.get(
                "train_number",
                ""
            )
        ),

        int(
            row.get(
                "stop_number",
                9999
            )
        )
        if str(
            row.get(
                "stop_number",
                ""
            )
        ).isdigit()
        else 9999
    )
)


# ==========================================================
# SAVE OUTPUT
# ==========================================================

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        assigned_records,
        file,
        indent=4,
        ensure_ascii=False
    )


# ==========================================================
# PLATFORM USAGE
# ==========================================================

platform_usage = defaultdict(int)


for row in assigned_records:

    platform_type = row.get(
        "platform_type"
    )

    if platform_type is None:

        platform_type = "UNKNOWN"


    platform_usage[
        platform_type
    ] += 1


# ==========================================================
# SUMMARY
# ==========================================================

print()
print("=" * 70)
print("PLATFORM ALLOCATION FINISHED")
print("=" * 70)

print()

print(
    f"Stations Processed      : "
    f"{len(station_records):,}"
)

print(
    f"Allocated Records       : "
    f"{allocation_count:,}"
)

print(
    f"Fallback Allocations    : "
    f"{fallback_count:,}"
)

print(
    f"Unassigned Records      : "
    f"{unassigned_count:,}"
)


print()
print("Platform Usage")


for platform_type in sorted(
    platform_usage
):

    print(
        f"{platform_type:<12} : "
        f"{platform_usage[platform_type]:,}"
    )


# ==========================================================
# EMU / MEMU SUMMARY
# ==========================================================

print()

print(
    f"EMU/MEMU Records              : "
    f"{small_train_records:,}"
)

print(
    f"EMU/MEMU on SUBURBAN          : "
    f"{small_train_suburban:,}"
)

print(
    f"EMU/MEMU on MAINLINE fallback : "
    f"{small_train_mainline_fallback:,}"
)


# ==========================================================
# OUTPUT
# ==========================================================

print()

print(
    f"Output Records          : "
    f"{len(assigned_records):,}"
)

print()

print("Saved To:")
print(OUTPUT_FILE)

print()

print("=" * 70)
print("PLATFORM ALLOCATION COMPLETED")
print("=" * 70)