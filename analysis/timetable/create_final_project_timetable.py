import json
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "project_timetable_platform_working.json"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "project_timetable"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "project_timetable_platform.json"
)


# ============================================================
# FINAL PROJECT STATIONS
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
# LOAD WORKING DATA
# ============================================================

print("=" * 70)
print("CREATING FINAL PROJECT TIMETABLE")
print("=" * 70)

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    timetable = json.load(f)

print(f"\nInput Records : {len(timetable)}")


# ============================================================
# FILTER PROJECT STATIONS
# ============================================================

project_records = [
    record
    for record in timetable
    if record.get("station_code") in PROJECT_STATIONS
]


# ============================================================
# VALIDATE PLATFORM ASSIGNMENTS
# ============================================================

missing_platform = [
    record
    for record in project_records
    if record.get("platform_number") is None
]

missing_platform_type = [
    record
    for record in project_records
    if record.get("platform_type") is None
]


if missing_platform:
    raise ValueError(
        f"Found {len(missing_platform)} records without platform numbers."
    )

if missing_platform_type:
    raise ValueError(
        f"Found {len(missing_platform_type)} records without platform types."
    )


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# SAVE FINAL DATASET
# ============================================================

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        project_records,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# SUMMARY
# ============================================================

used_stations = sorted(
    {
        record["station_code"]
        for record in project_records
    }
)

unused_stations = sorted(
    PROJECT_STATIONS - set(used_stations)
)


print("\n")
print("=" * 70)
print("FINAL PROJECT TIMETABLE CREATED")
print("=" * 70)

print(f"\nFinal Records          : {len(project_records)}")
print(f"Stations Represented   : {len(used_stations)}")
print(f"Platforms Missing      : {len(missing_platform)}")
print(f"Platform Types Missing : {len(missing_platform_type)}")

print("\nUnused Project Stations:")
print(unused_stations)

print("\nSaved To:")
print(OUTPUT_FILE)

print("\nIMPORTANT:")
print("The original timetable and working file were not modified.")