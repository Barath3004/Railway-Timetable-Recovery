import json
import os
from datetime import datetime, timedelta


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

# ------------------------------------------------------------
# Possible timetable locations
# ------------------------------------------------------------

TIMETABLE_CANDIDATES = [
    os.path.join(
        BASE_DIR,
        "data",
        "processed",
        "project_timetable_platform.json"
    ),

    os.path.join(
        BASE_DIR,
        "data",
        "processed",
        "project_timetable",
        "project_timetable_platform.json"
    )
]

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

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "resource"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "resource_allocation.json"
)


# ============================================================
# CONSTANTS
# ============================================================

MINUTES_PER_DAY = 24 * 60

SMALL_TRAIN_BUFFER_MINUTES = 5


# ============================================================
# HELPERS
# ============================================================

def parse_time(time_value):

    if time_value is None:
        return None

    value = str(time_value).strip()

    if value == "":
        return None

    if value.lower() in {
        "none",
        "null",
        "--"
    }:
        return None

    try:

        return datetime.strptime(
            value,
            "%H:%M:%S"
        )

    except ValueError:

        return None


def format_time(dt):

    if dt is None:
        return None

    return dt.strftime("%H:%M:%S")


def normalize_platform_type(value):

    if value is None:
        return None

    value = str(
        value
    ).strip().upper()

    if value in {
        "MAINLINE",
        "SUBURBAN"
    }:

        return value

    return None


def normalize_platform_number(value):

    if value is None:
        return None

    try:

        return int(value)

    except (
        ValueError,
        TypeError
    ):

        return None


def get_day(record):

    try:

        return int(
            record.get(
                "day",
                1
            )
        )

    except (
        ValueError,
        TypeError
    ):

        return 1


def is_small_train(train_type):

    if train_type is None:
        return False

    return str(
        train_type
    ).strip().upper() in {
        "EMU",
        "MEMU"
    }


# ============================================================
# START
# ============================================================

print("=" * 70)
print("CREATING RESOURCE ALLOCATION DATASET")
print("=" * 70)

print()


# ============================================================
# FIND TIMETABLE
# ============================================================

TIMETABLE_FILE = None

for candidate in TIMETABLE_CANDIDATES:

    if os.path.exists(candidate):

        TIMETABLE_FILE = candidate

        break


if TIMETABLE_FILE is None:

    raise FileNotFoundError(
        "Could not find project_timetable_platform.json.\n\n"
        "Checked:\n"
        + "\n".join(TIMETABLE_CANDIDATES)
    )


print(
    "Timetable Source:"
)

print(
    TIMETABLE_FILE
)

print()


# ============================================================
# LOAD TRAIN MASTER
# ============================================================

if not os.path.exists(
    TRAIN_MASTER_FILE
):

    raise FileNotFoundError(
        f"Train master not found:\n"
        f"{TRAIN_MASTER_FILE}"
    )


with open(
    TRAIN_MASTER_FILE,
    "r",
    encoding="utf-8"
) as file:

    train_master = json.load(file)


if not isinstance(
    train_master,
    list
):

    raise ValueError(
        "Train master must contain a JSON list."
    )


# ============================================================
# TRAIN LOOKUP
# ============================================================

train_lookup = {}

for train in train_master:

    train_number = str(
        train.get(
            "train_number",
            ""
        )
    ).strip()

    if train_number:

        train_lookup[
            train_number
        ] = train


print(
    f"Train Master Loaded    : "
    f"{len(train_master):,}"
)


# ============================================================
# LOAD STATION PROFILE
# ============================================================

if not os.path.exists(
    STATION_PROFILE_FILE
):

    raise FileNotFoundError(
        f"Station platform profile not found:\n"
        f"{STATION_PROFILE_FILE}"
    )


with open(
    STATION_PROFILE_FILE,
    "r",
    encoding="utf-8"
) as file:

    station_profiles = json.load(file)


if not isinstance(
    station_profiles,
    list
):

    raise ValueError(
        "Station platform profile must contain a JSON list."
    )


print(
    f"Station Profiles Loaded: "
    f"{len(station_profiles):,}"
)


# ============================================================
# BUILD STATION PROFILE LOOKUP
# ============================================================

station_profile_lookup = {}


for profile in station_profiles:

    station_code = profile.get(
        "station_code"
    )

    if not station_code:
        continue

    station_code = str(
        station_code
    ).strip().upper()


    # --------------------------------------------------------
    # BUFFER
    # --------------------------------------------------------

    buffer_value = profile.get(
        "station_buffer_minutes"
    )

    try:

        buffer_value = int(
            buffer_value
        )

    except (
        ValueError,
        TypeError
    ):

        buffer_value = None


    # --------------------------------------------------------
    # PLATFORM LOOKUP
    # --------------------------------------------------------

    platforms = {}


    for platform in profile.get(
        "platforms",
        []
    ):

        platform_number = normalize_platform_number(
            platform.get(
                "platform_number"
            )
        )

        platform_type = normalize_platform_type(
            platform.get(
                "platform_type"
            )
        )

        if (
            platform_number is None
            or platform_type is None
        ):

            continue


        platforms[
            platform_number
        ] = platform_type


    station_profile_lookup[
        station_code
    ] = {

        "station_name": profile.get(
            "station_name"
        ),

        "platforms_total": profile.get(
            "platforms_total"
        ),

        "buffer_minutes": buffer_value,

        "platforms": platforms
    }


# ============================================================
# LOAD PLATFORM TIMETABLE
# ============================================================

with open(
    TIMETABLE_FILE,
    "r",
    encoding="utf-8"
) as file:

    timetable = json.load(file)


if not isinstance(
    timetable,
    list
):

    raise ValueError(
        "Project timetable must contain a JSON list."
    )


print(
    f"Timetable Records      : "
    f"{len(timetable):,}"
)

print()


# ============================================================
# CREATE RESOURCE ALLOCATIONS
# ============================================================

resource_allocations = []


# ------------------------------------------------------------
# Statistics
# ------------------------------------------------------------

skipped_no_platform = 0
skipped_invalid_station = 0
skipped_invalid_platform = 0
skipped_invalid_time = 0
skipped_missing_id = 0
skipped_missing_buffer = 0

fallback_count = 0

overnight_count = 0

small_train_count = 0
small_train_buffer_count = 0
normal_train_buffer_count = 0

zero_duration = 0


# ============================================================
# PROCESS TIMETABLE
# ============================================================

for record in timetable:

    # ========================================================
    # TIMETABLE RECORD ID
    # ========================================================

    timetable_record_id = record.get(
        "id"
    )

    if timetable_record_id is None:

        skipped_missing_id += 1

        continue


    # ========================================================
    # STATION
    # ========================================================

    station_code = record.get(
        "station_code"
    )

    if station_code is None:

        skipped_invalid_station += 1

        continue


    station_code = str(
        station_code
    ).strip().upper()


    profile = station_profile_lookup.get(
        station_code
    )

    if profile is None:

        skipped_invalid_station += 1

        continue


    station_name = record.get(
        "station_name"
    )

    if not station_name:

        station_name = profile.get(
            "station_name"
        )


    # ========================================================
    # PLATFORM
    # ========================================================

    platform_number = normalize_platform_number(
        record.get(
            "platform_number"
        )
    )

    if platform_number is None:

        skipped_no_platform += 1

        continue


    platform_type = normalize_platform_type(
        record.get(
            "platform_type"
        )
    )

    if platform_type is None:

        skipped_no_platform += 1

        continue


    # ========================================================
    # VALIDATE PLATFORM
    # ========================================================

    profile_platform_type = profile[
        "platforms"
    ].get(
        platform_number
    )


    if profile_platform_type is None:

        skipped_invalid_platform += 1

        continue


    if platform_type != profile_platform_type:

        skipped_invalid_platform += 1

        continue


    # ========================================================
    # DAY
    # ========================================================

    day = get_day(
        record
    )


    # ========================================================
    # TIME
    # ========================================================

    arrival_dt = parse_time(
        record.get(
            "arrival"
        )
    )

    departure_dt = parse_time(
        record.get(
            "departure"
        )
    )


    if (
        arrival_dt is None
        and departure_dt is None
    ):

        skipped_invalid_time += 1

        continue


    # ========================================================
    # DETERMINE START / END
    # ========================================================

    if arrival_dt is not None:

        allocation_start_dt = arrival_dt

    else:

        allocation_start_dt = departure_dt


    if departure_dt is not None:

        allocation_end_dt = departure_dt

    else:

        allocation_end_dt = arrival_dt


    # ========================================================
    # OVERNIGHT HANDLING
    # ========================================================

    end_day = day


    if (
        arrival_dt is not None
        and departure_dt is not None
        and departure_dt < arrival_dt
    ):

        allocation_end_dt = (
            departure_dt
            + timedelta(
                days=1
            )
        )

        end_day = day + 1

        overnight_count += 1


    # ========================================================
    # OCCUPANCY
    # ========================================================

    occupancy_seconds = (
        allocation_end_dt
        - allocation_start_dt
    ).total_seconds()


    if occupancy_seconds < 0:

        skipped_invalid_time += 1

        continue


    occupancy_minutes = int(
        occupancy_seconds // 60
    )


    if occupancy_minutes == 0:

        zero_duration += 1


    # ========================================================
    # TRAIN TYPE
    # ========================================================

    train_number = str(
        record.get(
            "train_number",
            ""
        )
    ).strip()


    train = train_lookup.get(
        train_number
    )


    if train is not None:

        train_type = train.get(
            "train_type",
            "Express"
        )

    else:

        train_type = "Express"


    small_train = is_small_train(
        train_type
    )


    # ========================================================
    # BUFFER
    # ========================================================

    station_buffer = profile.get(
        "buffer_minutes"
    )


    if station_buffer is None:

        skipped_missing_buffer += 1

        continue


    if small_train:

        buffer_minutes = (
            SMALL_TRAIN_BUFFER_MINUTES
        )

        small_train_count += 1
        small_train_buffer_count += 1

    else:

        buffer_minutes = station_buffer

        normal_train_buffer_count += 1


    # ========================================================
    # RELEASE TIME
    # ========================================================

    release_dt = (
        allocation_end_dt
        + timedelta(
            minutes=buffer_minutes
        )
    )


    release_day = end_day


    # --------------------------------------------------------
    # If release passes midnight again, preserve that day.
    # --------------------------------------------------------

    if release_dt.date() > allocation_end_dt.date():

        release_day = end_day + (
            release_dt.date()
            - allocation_end_dt.date()
        ).days


    release_time = format_time(
        release_dt
    )


    # ========================================================
    # RESOURCE ID
    # ========================================================

    resource_id = (
        f"{station_code}-P{platform_number}"
    )


    # ========================================================
    # ALLOCATION SOURCE
    # ========================================================

    allocation_source = record.get(
        "platform_allocated_by",
        "AUTO"
    )


    if allocation_source is None:

        allocation_source = "AUTO"


    allocation_source = str(
        allocation_source
    ).strip().upper()


    if allocation_source == "AUTO_FALLBACK":

        fallback_count += 1

    else:

        allocation_source = "AUTO"


    # ========================================================
    # CREATE RESOURCE ALLOCATION
    # ========================================================

    allocation = {

        # ----------------------------------------------------
        # Identity
        # ----------------------------------------------------

        "allocation_id": None,

        # ----------------------------------------------------
        # Resource
        # ----------------------------------------------------

        "resource_id": resource_id,

        "resource_type": "PLATFORM",

        # ----------------------------------------------------
        # Station
        # ----------------------------------------------------

        "station_code": station_code,

        "station_name": station_name,

        # ----------------------------------------------------
        # Platform
        # ----------------------------------------------------

        "platform_number": platform_number,

        "platform_type": platform_type,

        # ----------------------------------------------------
        # Scheduling day
        # ----------------------------------------------------

        "day": day,

        "allocation_end_day": end_day,

        "release_day": release_day,

        # ----------------------------------------------------
        # Timetable bridge
        # ----------------------------------------------------

        "timetable_record_id": timetable_record_id,

        # ----------------------------------------------------
        # Occupancy
        # ----------------------------------------------------

        "allocation_start": format_time(
            allocation_start_dt
        ),

        "allocation_end": format_time(
            allocation_end_dt
        ),

        "occupancy_minutes": occupancy_minutes,

        # ----------------------------------------------------
        # Buffer / release
        # ----------------------------------------------------

        "buffer_minutes": buffer_minutes,

        "release_time": release_time,

        # ----------------------------------------------------
        # State
        # ----------------------------------------------------

        "allocation_status": "ALLOCATED",

        "allocation_source": allocation_source
    }


    resource_allocations.append(
        allocation
    )


# ============================================================
# SORT
# ============================================================

resource_allocations.sort(
    key=lambda x: (
        x["station_code"],
        x["platform_number"],
        x["day"],
        x["allocation_start"] or "",
        x["timetable_record_id"]
    )
)


# ============================================================
# GENERATE DETERMINISTIC IDs
# ============================================================

for index, allocation in enumerate(
    resource_allocations,
    start=1
):

    allocation[
        "allocation_id"
    ] = f"RA{index:06d}"


# ============================================================
# SAVE
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        resource_allocations,
        file,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# SUMMARY STATISTICS
# ============================================================

platform_resources = {
    allocation[
        "resource_id"
    ]

    for allocation
    in resource_allocations
}


stations = {
    allocation[
        "station_code"
    ]

    for allocation
    in resource_allocations
}


mainline = sum(
    1

    for allocation
    in resource_allocations

    if allocation[
        "platform_type"
    ] == "MAINLINE"
)


suburban = sum(
    1

    for allocation
    in resource_allocations

    if allocation[
        "platform_type"
    ] == "SUBURBAN"
)


# ============================================================
# FINAL REPORT
# ============================================================

print()

print("=" * 70)
print("RESOURCE ALLOCATION DATASET CREATED")
print("=" * 70)

print()

print(
    f"Allocation Records      : "
    f"{len(resource_allocations):,}"
)

print(
    f"Stations Represented    : "
    f"{len(stations):,}"
)

print(
    f"Platform Resources      : "
    f"{len(platform_resources):,}"
)

print()

print("PLATFORM TYPE")
print("-" * 70)

print(
    f"MAINLINE                : "
    f"{mainline:,}"
)

print(
    f"SUBURBAN                : "
    f"{suburban:,}"
)

print()

print("RESOURCE ALLOCATION")
print("-" * 70)

print(
    f"Fallback Allocations    : "
    f"{fallback_count:,}"
)

print(
    f"Zero-Duration Records   : "
    f"{zero_duration:,}"
)

print(
    f"Overnight Records       : "
    f"{overnight_count:,}"
)

print()

print("BUFFER LOGIC")
print("-" * 70)

print(
    f"EMU/MEMU Records        : "
    f"{small_train_count:,}"
)

print(
    f"EMU/MEMU 5-min Buffer   : "
    f"{small_train_buffer_count:,}"
)

print(
    f"Normal Train Buffer     : "
    f"{normal_train_buffer_count:,}"
)

print()

print("SKIPPED RECORDS")
print("-" * 70)

print(
    f"Missing Platform        : "
    f"{skipped_no_platform:,}"
)

print(
    f"Invalid Station         : "
    f"{skipped_invalid_station:,}"
)

print(
    f"Invalid Platform        : "
    f"{skipped_invalid_platform:,}"
)

print(
    f"Invalid Time            : "
    f"{skipped_invalid_time:,}"
)

print(
    f"Missing Timetable ID    : "
    f"{skipped_missing_id:,}"
)

print(
    f"Missing Station Buffer  : "
    f"{skipped_missing_buffer:,}"
)

print()

print("Output:")
print(
    OUTPUT_FILE
)

print()

print("=" * 70)
print("DONE")
print("=" * 70)