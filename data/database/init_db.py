import json
import csv
import sqlite3
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

EXPECTED_TRAINS = 552
EXPECTED_STATIONS = 32
EXPECTED_PLATFORMS = 176
EXPECTED_TIMETABLE = 2469
EXPECTED_RESOURCE_ALLOCATIONS = 2445

EXCLUDED_STATIONS = {
    "CAPE",
    "CUPJ",
    "RMD",
    "SVKS",
}


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TRAIN_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "trains"
    / "train_master.json"
)

STATION_REFERENCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "stations"
    / "station_reference.csv"
)

STATION_PROFILE_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "platforms"
    / "station_platform_profile.json"
)

TIMETABLE_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "project_timetable"
    / "project_timetable_platform.json"
)

RESOURCE_ALLOCATION_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "resource"
    / "resource_allocation.json"
)

DATABASE_FILE = (
    PROJECT_ROOT
    / "data"
    / "database"
    / "railway_recovery.db"
)


# ============================================================
# HELPERS
# ============================================================

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_none(value):
    """
    Convert source representations of missing values to None.
    """
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()

        if value.lower() in {
            "",
            "none",
            "null",
            "nan",
        }:
            return None

    return value


def find_list(data, possible_keys):
    """
    Extract a list from either:
      - a direct JSON list
      - a dictionary containing the list under a known key
    """
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in possible_keys:
            if key in data and isinstance(data[key], list):
                return data[key]

    raise ValueError(
        f"Could not find list data. Expected keys: {possible_keys}"
    )


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("RAILWAY TIMETABLE RECOVERY DATABASE INITIALIZATION")
print("=" * 70)

print()
print("Project root:")
print(PROJECT_ROOT)

print()
print("Database:")
print(DATABASE_FILE)


# ============================================================
# CHECK SOURCE FILES
# ============================================================

print()
print("=" * 70)
print("CHECKING SOURCE FILES")
print("=" * 70)

source_files = [
    ("train_master.json", TRAIN_FILE),
    ("station_reference.csv", STATION_REFERENCE_FILE),
    ("station_platform_profile.json", STATION_PROFILE_FILE),
    ("project_timetable_platform.json", TIMETABLE_FILE),
    ("resource_allocation.json", RESOURCE_ALLOCATION_FILE),
]

for name, path in source_files:
    if not path.exists():
        raise FileNotFoundError(
            f"Required source file not found:\n{path}"
        )

    print(f"FOUND: {path.relative_to(PROJECT_ROOT)}")


# ============================================================
# LOAD SOURCE DATA
# ============================================================

print()
print("=" * 70)
print("LOADING SOURCE DATA")
print("=" * 70)


# -----------------------------
# TRAIN MASTER
# -----------------------------

train_data_raw = load_json(TRAIN_FILE)

trains = find_list(
    train_data_raw,
    ["trains", "train_master", "data"]
)


# -----------------------------
# STATION REFERENCE
# -----------------------------

stations_reference = []

with open(
    STATION_REFERENCE_FILE,
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:

    reader = csv.DictReader(f)

    for row in reader:
        stations_reference.append(row)


# -----------------------------
# STATION PLATFORM PROFILE
# -----------------------------

station_profile_raw = load_json(STATION_PROFILE_FILE)

station_profiles = find_list(
    station_profile_raw,
    ["stations", "station_profiles", "data"]
)


# -----------------------------
# TIMETABLE
# -----------------------------

timetable_raw = load_json(TIMETABLE_FILE)

timetable = find_list(
    timetable_raw,
    ["timetable", "records", "data"]
)


# -----------------------------
# RESOURCE ALLOCATION
# -----------------------------

resource_raw = load_json(RESOURCE_ALLOCATION_FILE)

resource_allocations = find_list(
    resource_raw,
    [
        "resource_allocations",
        "allocations",
        "resource_allocation",
        "data",
    ]
)


print(f"Trains in source                 : {len(trains)}")
print(f"Stations in source              : {len(stations_reference)}")
print(f"Station profiles in source      : {len(station_profiles)}")
print(f"Timetable records in source     : {len(timetable)}")
print(f"Resource allocations in source  : {len(resource_allocations)}")


# ============================================================
# EXCLUDED STATIONS
# ============================================================

print()
print("Excluded stations:")

for station_code in sorted(EXCLUDED_STATIONS):
    print(f"  - {station_code}")


# ============================================================
# BUILD PROJECT STATIONS
# ============================================================

project_station_codes = set()

for row in timetable:

    station_code = normalize_none(
        row.get("station_code")
    )

    if station_code and station_code not in EXCLUDED_STATIONS:
        project_station_codes.add(station_code)


print()
print(
    f"Final project stations          : "
    f"{len(project_station_codes)}"
)


# ============================================================
# BUILD STATION MASTER
# ============================================================

reference_by_code = {}

for row in stations_reference:

    code = normalize_none(
        row.get("station_code")
        or row.get("code")
    )

    if code:
        reference_by_code[code] = row


profile_by_code = {}

for row in station_profiles:

    code = normalize_none(
        row.get("station_code")
        or row.get("code")
    )

    if code:
        profile_by_code[code] = row


stations = []

for station_code in sorted(project_station_codes):

    reference = reference_by_code.get(
        station_code,
        {}
    )

    profile = profile_by_code.get(
        station_code,
        {}
    )

    station = {
        "station_code": station_code,

        "station_name": normalize_none(
            profile.get("station_name")
            or reference.get("station_name")
            or reference.get("name")
        ),

        "railway_zone": normalize_none(
            reference.get("railway_zone")
            or reference.get("zone")
        ),

        "railway_division": normalize_none(
            reference.get("railway_division")
            or reference.get("division")
        ),

        "platforms_total": normalize_none(
            profile.get("platforms_total")
        ),

        "mainline_platforms": normalize_none(
            profile.get("mainline_platforms")
        ),

        "suburban_platforms": normalize_none(
            profile.get("suburban_platforms")
        ),

        "electrification_year": normalize_none(
            profile.get("electrification_year")
        ),

        "station_buffer_minutes": normalize_none(
            profile.get("station_buffer_minutes")
        ),
    }

    stations.append(station)


# ============================================================
# BUILD PLATFORM MASTER
# ============================================================

platforms = []

for station_profile in station_profiles:

    station_code = normalize_none(
        station_profile.get("station_code")
    )

    if not station_code:
        continue

    if station_code in EXCLUDED_STATIONS:
        continue

    station_platforms = station_profile.get(
        "platforms",
        []
    )

    for platform in station_platforms:

        platform_number = normalize_none(
            platform.get("platform_number")
        )

        platform_type = normalize_none(
            platform.get("platform_type")
        )

        if platform_number is None:
            continue

        resource_id = (
            f"{station_code}-P{platform_number}"
        )

        platforms.append({
            "resource_id": resource_id,
            "station_code": station_code,
            "platform_number": int(platform_number),
            "platform_type": (
                platform_type
                if platform_type
                else "UNKNOWN"
            ),
            "resource_type": "PLATFORM",
        })


# Remove duplicate station/platform pairs
unique_platforms = {}

for platform in platforms:

    key = (
        platform["station_code"],
        platform["platform_number"],
    )

    unique_platforms[key] = platform


platforms = list(unique_platforms.values())


print(
    f"Final project platforms         : "
    f"{len(platforms)}"
)


# ============================================================
# PRE-DATABASE VALIDATION
# ============================================================

print()
print("=" * 70)
print("PRE-DATABASE VALIDATION")
print("=" * 70)


unique_train_numbers = {
    normalize_none(
        train.get("train_number")
    )
    for train in trains
}

unique_train_numbers.discard(None)


unique_station_codes = {
    station["station_code"]
    for station in stations
}


unique_platform_pairs = {
    (
        platform["station_code"],
        platform["platform_number"]
    )
    for platform in platforms
}


unique_timetable_ids = {
    normalize_none(
        row.get("id")
    )
    for row in timetable
}

unique_timetable_ids.discard(None)


print(
    f"Unique train numbers             : "
    f"{len(unique_train_numbers)}"
)

print(
    f"Unique project station codes    : "
    f"{len(unique_station_codes)}"
)

print(
    f"Unique station/platform pairs   : "
    f"{len(unique_platform_pairs)}"
)

print(
    f"Unique timetable IDs             : "
    f"{len(unique_timetable_ids)}"
)


# -----------------------------
# Train references
# -----------------------------

invalid_train_refs = []

for row in timetable:

    train_number = normalize_none(
        row.get("train_number")
    )

    if train_number not in unique_train_numbers:
        invalid_train_refs.append(
            row.get("id")
        )


print(
    "Train references                : "
    + (
        "PASS"
        if not invalid_train_refs
        else f"FAIL ({len(invalid_train_refs)})"
    )
)


# -----------------------------
# Station references
# -----------------------------

invalid_station_refs = []

for row in timetable:

    station_code = normalize_none(
        row.get("station_code")
    )

    if station_code not in unique_station_codes:
        invalid_station_refs.append(
            row.get("id")
        )


print(
    "Station references              : "
    + (
        "PASS"
        if not invalid_station_refs
        else f"FAIL ({len(invalid_station_refs)})"
    )
)


# -----------------------------
# Platform references
# -----------------------------

invalid_platform_refs = []

for row in timetable:

    station_code = normalize_none(
        row.get("station_code")
    )

    platform_number = normalize_none(
        row.get("platform_number")
    )

    if station_code in EXCLUDED_STATIONS:
        invalid_platform_refs.append(
            row.get("id")
        )
        continue

    if platform_number is None:
        invalid_platform_refs.append(
            row.get("id")
        )
        continue

    try:
        platform_number = int(platform_number)
    except (ValueError, TypeError):
        invalid_platform_refs.append(
            row.get("id")
        )
        continue

    if (
        station_code,
        platform_number
    ) not in unique_platform_pairs:

        invalid_platform_refs.append(
            row.get("id")
        )


print(
    "Platform references             : "
    + (
        "PASS"
        if not invalid_platform_refs
        else f"FAIL ({len(invalid_platform_refs)})"
    )
)


# ============================================================
# RESOURCE ALLOCATION VALIDATION
# ============================================================

print()
print("=" * 70)
print("RESOURCE ALLOCATION VALIDATION")
print("=" * 70)


allocation_ids = set()
duplicate_allocation_ids = []

for allocation in resource_allocations:

    allocation_id = normalize_none(
        allocation.get("allocation_id")
        or allocation.get("id")
    )

    if allocation_id in allocation_ids:
        duplicate_allocation_ids.append(
            allocation_id
        )

    allocation_ids.add(allocation_id)


print(
    f"Resource allocations            : "
    f"{len(resource_allocations)}"
)

print(
    "Unique allocation IDs            : "
    + (
        "PASS"
        if not duplicate_allocation_ids
        else f"FAIL ({len(duplicate_allocation_ids)})"
    )
)


# -----------------------------
# Allocation → timetable refs
# -----------------------------

timetable_id_set = {
    int(x)
    for x in unique_timetable_ids
    if str(x).isdigit()
}


invalid_allocation_timetable_refs = []

for allocation in resource_allocations:

    timetable_record_id = normalize_none(
        allocation.get("timetable_record_id")
    )

    try:
        timetable_record_id = int(
            timetable_record_id
        )
    except (ValueError, TypeError):
        invalid_allocation_timetable_refs.append(
            allocation.get("allocation_id")
        )
        continue

    if timetable_record_id not in timetable_id_set:

        invalid_allocation_timetable_refs.append(
            allocation.get("allocation_id")
        )


print(
    "Allocation → Timetable references : "
    + (
        "PASS"
        if not invalid_allocation_timetable_refs
        else (
            f"FAIL "
            f"({len(invalid_allocation_timetable_refs)})"
        )
    )
)


# -----------------------------
# Allocation → platform refs
# -----------------------------

invalid_allocation_platform_refs = []

for allocation in resource_allocations:

    station_code = normalize_none(
        allocation.get("station_code")
    )

    platform_number = normalize_none(
        allocation.get("platform_number")
    )

    if station_code in EXCLUDED_STATIONS:
        invalid_allocation_platform_refs.append(
            allocation.get("allocation_id")
        )
        continue

    try:
        platform_number = int(platform_number)
    except (ValueError, TypeError):
        invalid_allocation_platform_refs.append(
            allocation.get("allocation_id")
        )
        continue

    if (
        station_code,
        platform_number
    ) not in unique_platform_pairs:

        invalid_allocation_platform_refs.append(
            allocation.get("allocation_id")
        )


print(
    "Allocation → Platform references  : "
    + (
        "PASS"
        if not invalid_allocation_platform_refs
        else (
            f"FAIL "
            f"({len(invalid_allocation_platform_refs)})"
        )
    )
)


# ============================================================
# CREATE DATABASE
# ============================================================

print()
print("=" * 70)
print("CREATING SQLITE DATABASE")
print("=" * 70)


DATABASE_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)


# Remove previous database
if DATABASE_FILE.exists():
    DATABASE_FILE.unlink()


connection = sqlite3.connect(
    DATABASE_FILE
)

cursor = connection.cursor()


# Enable foreign keys
cursor.execute(
    "PRAGMA foreign_keys = ON;"
)


# ============================================================
# TABLE: TRAINS
# ============================================================

cursor.execute("""
CREATE TABLE trains (
    train_number TEXT PRIMARY KEY,
    train_name TEXT NOT NULL,
    train_type TEXT NOT NULL,
    priority INTEGER,
    maximum_speed_kmph REAL,
    operator TEXT,
    zone TEXT,
    source_station TEXT,
    destination_station TEXT
);
""")


# ============================================================
# TABLE: STATIONS
# ============================================================

cursor.execute("""
CREATE TABLE stations (
    station_code TEXT PRIMARY KEY,
    station_name TEXT NOT NULL,
    railway_zone TEXT,
    railway_division TEXT,
    platforms_total INTEGER,
    mainline_platforms INTEGER,
    suburban_platforms INTEGER,
    electrification_year INTEGER,
    station_buffer_minutes INTEGER
);
""")


# ============================================================
# TABLE: PLATFORMS
# ============================================================

cursor.execute("""
CREATE TABLE platforms (
    resource_id TEXT PRIMARY KEY,
    station_code TEXT NOT NULL,
    platform_number INTEGER NOT NULL,
    platform_type TEXT NOT NULL,
    resource_type TEXT NOT NULL DEFAULT 'PLATFORM',

    FOREIGN KEY (station_code)
        REFERENCES stations(station_code),

    UNIQUE (
        station_code,
        platform_number
    )
);
""")


# ============================================================
# TABLE: TIMETABLE
# ============================================================

cursor.execute("""
CREATE TABLE timetable (
    timetable_record_id INTEGER PRIMARY KEY,

    train_number TEXT NOT NULL,
    station_code TEXT NOT NULL,

    day INTEGER NOT NULL,
    stop_number INTEGER NOT NULL,

    arrival TEXT,
    departure TEXT,

    resource_id TEXT,
    platform_number INTEGER,
    platform_type TEXT,
    platform_allocated_by TEXT,

    FOREIGN KEY (train_number)
        REFERENCES trains(train_number),

    FOREIGN KEY (station_code)
        REFERENCES stations(station_code),

    FOREIGN KEY (resource_id)
        REFERENCES platforms(resource_id)
);
""")


# ============================================================
# TABLE: RESOURCE ALLOCATIONS
# ============================================================

cursor.execute("""
CREATE TABLE resource_allocations (
    allocation_id TEXT PRIMARY KEY,

    resource_id TEXT NOT NULL,
    resource_type TEXT NOT NULL,

    station_code TEXT NOT NULL,
    station_name TEXT,

    platform_number INTEGER,
    platform_type TEXT,

    day INTEGER,

    timetable_record_id INTEGER NOT NULL,

    allocation_start TEXT,
    allocation_end TEXT,

    occupancy_minutes INTEGER,
    buffer_minutes INTEGER,

    release_time TEXT,

    allocation_status TEXT,
    allocation_source TEXT,

    FOREIGN KEY (resource_id)
        REFERENCES platforms(resource_id),

    FOREIGN KEY (station_code)
        REFERENCES stations(station_code),

    FOREIGN KEY (timetable_record_id)
        REFERENCES timetable(timetable_record_id)
);
""")


print()
print("5 database tables created successfully.")


# ============================================================
# INSERT TRAINS
# ============================================================

train_rows = []

for train in trains:

    train_number = normalize_none(
        train.get("train_number")
    )

    train_rows.append((
        train_number,
        normalize_none(
            train.get("train_name")
        ) or "",
        normalize_none(
            train.get("train_type")
        ) or "",
        normalize_none(
            train.get("priority")
        ),
        normalize_none(
            train.get("maximum_speed_kmph")
        ),
        normalize_none(
            train.get("operator")
        ),
        normalize_none(
            train.get("zone")
        ),
        normalize_none(
            train.get("source_station")
        ),
        normalize_none(
            train.get("destination_station")
        ),
    ))


cursor.executemany("""
INSERT INTO trains (
    train_number,
    train_name,
    train_type,
    priority,
    maximum_speed_kmph,
    operator,
    zone,
    source_station,
    destination_station
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
""", train_rows)


# ============================================================
# INSERT STATIONS
# ============================================================

station_rows = []

for station in stations:

    station_rows.append((
        station["station_code"],
        station["station_name"] or "",
        station["railway_zone"],
        station["railway_division"],
        station["platforms_total"],
        station["mainline_platforms"],
        station["suburban_platforms"],
        station["electrification_year"],
        station["station_buffer_minutes"],
    ))


cursor.executemany("""
INSERT INTO stations (
    station_code,
    station_name,
    railway_zone,
    railway_division,
    platforms_total,
    mainline_platforms,
    suburban_platforms,
    electrification_year,
    station_buffer_minutes
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
""", station_rows)


# ============================================================
# INSERT PLATFORMS
# ============================================================

platform_rows = []

for platform in platforms:

    platform_rows.append((
        platform["resource_id"],
        platform["station_code"],
        platform["platform_number"],
        platform["platform_type"],
        platform["resource_type"],
    ))


cursor.executemany("""
INSERT INTO platforms (
    resource_id,
    station_code,
    platform_number,
    platform_type,
    resource_type
)
VALUES (?, ?, ?, ?, ?);
""", platform_rows)


# ============================================================
# INSERT TIMETABLE
# ============================================================

timetable_rows = []

for row in timetable:

    timetable_id = int(
        row["id"]
    )

    train_number = normalize_none(
        row.get("train_number")
    )

    station_code = normalize_none(
        row.get("station_code")
    )

    platform_number = normalize_none(
        row.get("platform_number")
    )

    if platform_number is not None:
        platform_number = int(
            platform_number
        )

    resource_id = None

    if (
        station_code
        and platform_number is not None
    ):
        resource_id = (
            f"{station_code}-P{platform_number}"
        )

    timetable_rows.append((
        timetable_id,
        train_number,
        station_code,
        int(row.get("day")),
        int(row.get("stop_number")),
        normalize_none(row.get("arrival")),
        normalize_none(row.get("departure")),
        resource_id,
        platform_number,
        normalize_none(
            row.get("platform_type")
        ),
        normalize_none(
            row.get("platform_allocated_by")
        ),
    ))


cursor.executemany("""
INSERT INTO timetable (
    timetable_record_id,
    train_number,
    station_code,
    day,
    stop_number,
    arrival,
    departure,
    resource_id,
    platform_number,
    platform_type,
    platform_allocated_by
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
""", timetable_rows)


# ============================================================
# INSERT RESOURCE ALLOCATIONS
# ============================================================

allocation_rows = []

for allocation in resource_allocations:

    allocation_id = normalize_none(
        allocation.get("allocation_id")
        or allocation.get("id")
    )

    resource_id = normalize_none(
        allocation.get("resource_id")
    )

    resource_type = normalize_none(
        allocation.get("resource_type")
    )

    station_code = normalize_none(
        allocation.get("station_code")
    )

    station_name = normalize_none(
        allocation.get("station_name")
    )

    platform_number = normalize_none(
        allocation.get("platform_number")
    )

    if platform_number is not None:
        platform_number = int(
            platform_number
        )

    platform_type = normalize_none(
        allocation.get("platform_type")
    )

    day = normalize_none(
        allocation.get("day")
    )

    if day is not None:
        day = int(day)

    timetable_record_id = normalize_none(
        allocation.get("timetable_record_id")
    )

    if timetable_record_id is not None:
        timetable_record_id = int(
            timetable_record_id
        )

    occupancy_minutes = normalize_none(
        allocation.get("occupancy_minutes")
    )

    if occupancy_minutes is not None:
        occupancy_minutes = int(
            occupancy_minutes
        )

    buffer_minutes = normalize_none(
        allocation.get("buffer_minutes")
    )

    if buffer_minutes is not None:
        buffer_minutes = int(
            buffer_minutes
        )

    allocation_rows.append((
        allocation_id,
        resource_id,
        resource_type,
        station_code,
        station_name,
        platform_number,
        platform_type,
        day,
        timetable_record_id,
        normalize_none(
            allocation.get("allocation_start")
        ),
        normalize_none(
            allocation.get("allocation_end")
        ),
        occupancy_minutes,
        buffer_minutes,
        normalize_none(
            allocation.get("release_time")
        ),
        normalize_none(
            allocation.get("allocation_status")
        ),
        normalize_none(
            allocation.get("allocation_source")
        ),
    ))


cursor.executemany("""
INSERT INTO resource_allocations (
    allocation_id,
    resource_id,
    resource_type,
    station_code,
    station_name,
    platform_number,
    platform_type,
    day,
    timetable_record_id,
    allocation_start,
    allocation_end,
    occupancy_minutes,
    buffer_minutes,
    release_time,
    allocation_status,
    allocation_source
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
""", allocation_rows)


connection.commit()


# ============================================================
# INSERTION COUNTS
# ============================================================

train_count = cursor.execute(
    "SELECT COUNT(*) FROM trains"
).fetchone()[0]

station_count = cursor.execute(
    "SELECT COUNT(*) FROM stations"
).fetchone()[0]

platform_count = cursor.execute(
    "SELECT COUNT(*) FROM platforms"
).fetchone()[0]

timetable_count = cursor.execute(
    "SELECT COUNT(*) FROM timetable"
).fetchone()[0]

allocation_count = cursor.execute(
    "SELECT COUNT(*) FROM resource_allocations"
).fetchone()[0]


timetable_without_platform = cursor.execute("""
SELECT COUNT(*)
FROM timetable
WHERE resource_id IS NULL;
""").fetchone()[0]


print(
    f"Inserted trains                 : "
    f"{train_count}"
)

print(
    f"Inserted stations               : "
    f"{station_count}"
)

print(
    f"Inserted platforms              : "
    f"{platform_count}"
)

print(
    f"Inserted timetable records      : "
    f"{timetable_count}"
)

print(
    f"Inserted resource allocations   : "
    f"{allocation_count}"
)

print(
    f"Timetable without platform      : "
    f"{timetable_without_platform}"
)


# ============================================================
# DATABASE VALIDATION
# ============================================================

print()
print("=" * 70)
print("DATABASE VALIDATION")
print("=" * 70)


def check_count(label, expected, actual):
    status = "PASS" if expected == actual else "FAIL"

    print(
        f"{label:<30}"
        f"Expected={expected:<5} "
        f"Actual={actual:<5} "
        f"{status}"
    )

    return expected == actual


validation_pass = True

validation_pass &= check_count(
    "trains",
    EXPECTED_TRAINS,
    train_count
)

validation_pass &= check_count(
    "stations",
    EXPECTED_STATIONS,
    station_count
)

validation_pass &= check_count(
    "platforms",
    EXPECTED_PLATFORMS,
    platform_count
)

validation_pass &= check_count(
    "timetable",
    EXPECTED_TIMETABLE,
    timetable_count
)

validation_pass &= check_count(
    "resource_allocations",
    EXPECTED_RESOURCE_ALLOCATIONS,
    allocation_count
)


# ============================================================
# FOREIGN KEY CHECK
# ============================================================

foreign_key_errors = cursor.execute(
    "PRAGMA foreign_key_check;"
).fetchall()

fk_pass = len(foreign_key_errors) == 0

print(
    f"\nFOREIGN KEY CHECK                : "
    f"{'PASS' if fk_pass else 'FAIL'}"
)

if not fk_pass:

    for error in foreign_key_errors[:20]:
        print("  ", error)

validation_pass &= fk_pass


# ============================================================
# REFERENCE VALIDATION
# ============================================================

timetable_train_errors = cursor.execute("""
SELECT COUNT(*)
FROM timetable t
LEFT JOIN trains tr
    ON t.train_number = tr.train_number
WHERE tr.train_number IS NULL;
""").fetchone()[0]


timetable_station_errors = cursor.execute("""
SELECT COUNT(*)
FROM timetable t
LEFT JOIN stations s
    ON t.station_code = s.station_code
WHERE s.station_code IS NULL;
""").fetchone()[0]


timetable_platform_errors = cursor.execute("""
SELECT COUNT(*)
FROM timetable t
LEFT JOIN platforms p
    ON t.resource_id = p.resource_id
WHERE t.resource_id IS NOT NULL
  AND p.resource_id IS NULL;
""").fetchone()[0]


allocation_timetable_errors = cursor.execute("""
SELECT COUNT(*)
FROM resource_allocations ra
LEFT JOIN timetable t
    ON ra.timetable_record_id =
       t.timetable_record_id
WHERE t.timetable_record_id IS NULL;
""").fetchone()[0]


allocation_platform_errors = cursor.execute("""
SELECT COUNT(*)
FROM resource_allocations ra
LEFT JOIN platforms p
    ON ra.resource_id = p.resource_id
WHERE p.resource_id IS NULL;
""").fetchone()[0]


allocation_station_errors = cursor.execute("""
SELECT COUNT(*)
FROM resource_allocations ra
LEFT JOIN stations s
    ON ra.station_code = s.station_code
WHERE s.station_code IS NULL;
""").fetchone()[0]


print(
    "Timetable → Train references   : "
    + (
        "PASS"
        if timetable_train_errors == 0
        else f"FAIL ({timetable_train_errors})"
    )
)

print(
    "Timetable → Station references : "
    + (
        "PASS"
        if timetable_station_errors == 0
        else f"FAIL ({timetable_station_errors})"
    )
)

print(
    "Timetable → Platform references: "
    + (
        "PASS"
        if timetable_platform_errors == 0
        else f"FAIL ({timetable_platform_errors})"
    )
)

print(
    "Allocation → Timetable refs    : "
    + (
        "PASS"
        if allocation_timetable_errors == 0
        else f"FAIL ({allocation_timetable_errors})"
    )
)

print(
    "Allocation → Platform refs     : "
    + (
        "PASS"
        if allocation_platform_errors == 0
        else f"FAIL ({allocation_platform_errors})"
    )
)

print(
    "Allocation → Station refs      : "
    + (
        "PASS"
        if allocation_station_errors == 0
        else f"FAIL ({allocation_station_errors})"
    )
)


validation_pass &= (
    timetable_train_errors == 0
    and timetable_station_errors == 0
    and timetable_platform_errors == 0
    and allocation_timetable_errors == 0
    and allocation_platform_errors == 0
    and allocation_station_errors == 0
)


# ============================================================
# PLATFORM USAGE
# ============================================================

print()
print("=" * 70)
print("PLATFORM USAGE")
print("=" * 70)


used_platform_count = cursor.execute("""
SELECT COUNT(DISTINCT resource_id)
FROM timetable
WHERE resource_id IS NOT NULL;
""").fetchone()[0]


unused_platform_count = (
    platform_count - used_platform_count
)


auto_fallback_count = cursor.execute("""
SELECT COUNT(*)
FROM timetable
WHERE platform_allocated_by = 'AUTO_FALLBACK';
""").fetchone()[0]


print(
    f"Total project platforms          : "
    f"{platform_count}"
)

print(
    f"Platforms used by timetable     : "
    f"{used_platform_count}"
)

print(
    f"Platforms not used by timetable : "
    f"{unused_platform_count}"
)

print(
    f"AUTO_FALLBACK timetable records : "
    f"{auto_fallback_count}"
)


# ============================================================
# ALLOCATION COVERAGE
# ============================================================

print()
print("=" * 70)
print("RESOURCE ALLOCATION COVERAGE")
print("=" * 70)


allocated_timetable_count = cursor.execute("""
SELECT COUNT(DISTINCT timetable_record_id)
FROM resource_allocations;
""").fetchone()[0]


unallocated_timetable_count = cursor.execute("""
SELECT COUNT(*)
FROM timetable t
WHERE NOT EXISTS (
    SELECT 1
    FROM resource_allocations ra
    WHERE ra.timetable_record_id =
          t.timetable_record_id
);
""").fetchone()[0]


print(
    f"Timetable records               : "
    f"{timetable_count}"
)

print(
    f"Timetable records with allocation: "
    f"{allocated_timetable_count}"
)

print(
    f"Timetable records without allocation: "
    f"{unallocated_timetable_count}"
)


# ============================================================
# TABLE LIST
# ============================================================

print()
print("Database tables:")

tables = cursor.execute("""
SELECT name
FROM sqlite_master
WHERE type = 'table'
ORDER BY name;
""").fetchall()

for table in tables:
    print(f"  - {table[0]}")


# ============================================================
# FINAL RESULT
# ============================================================

if validation_pass:

    print()
    print("=" * 70)
    print("DATABASE INITIALIZATION COMPLETE")
    print("=" * 70)

    print()
    print("SUCCESS")

    print()
    print("Final architecture:")
    print(f"  trains                : {train_count}")
    print(f"  stations              : {station_count}")
    print(f"  platforms             : {platform_count}")
    print(f"  timetable             : {timetable_count}")
    print(f"  resource_allocations  : {allocation_count}")

    print()
    print("SQLite database:")
    print(DATABASE_FILE)

    connection.close()

else:

    print()
    print("=" * 70)
    print("DATABASE INITIALIZATION FAILED")
    print("=" * 70)

    connection.close()

    if DATABASE_FILE.exists():
        DATABASE_FILE.unlink()

    print()
    print("Database has been removed because validation failed.")
    raise SystemExit(1)