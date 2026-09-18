import json
from pathlib import Path
from collections import Counter, defaultdict


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

TRAIN_MASTER_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "train_master.json"
)


# ============================================================
# LOAD FINAL PROJECT TIMETABLE
# ============================================================

print("=" * 70)
print("VERIFY PLATFORM ALLOCATION BY TRAIN TYPE")
print("=" * 70)

with open(TIMETABLE_FILE, "r", encoding="utf-8") as f:
    timetable = json.load(f)

print(f"\nFinal Timetable Records : {len(timetable)}")


# ============================================================
# LOAD TRAIN MASTER
# ============================================================

with open(TRAIN_MASTER_FILE, "r", encoding="utf-8") as f:
    train_master = json.load(f)

print(f"Train Master Records    : {len(train_master)}")


# ============================================================
# INSPECT TRAIN MASTER STRUCTURE
# ============================================================

if isinstance(train_master, list):

    master_records = train_master

elif isinstance(train_master, dict):

    # Try common container names
    if "trains" in train_master:
        master_records = train_master["trains"]

    elif "data" in train_master:
        master_records = train_master["data"]

    else:
        master_records = []

else:

    master_records = []


# ============================================================
# BUILD TRAIN MASTER LOOKUP
# ============================================================

train_lookup = {}

for train in master_records:

    train_number = str(
        train.get("train_number")
        or train.get("train_no")
        or train.get("number")
        or ""
    ).strip()

    if train_number:

        train_lookup[train_number] = train


# ============================================================
# TRAIN TYPE COUNTS
# ============================================================

train_type_counts = Counter()

platform_type_by_train_type = defaultdict(Counter)

train_examples = defaultdict(list)

unknown_train_master = []

for record in timetable:

    train_number = str(
        record.get("train_number", "")
    ).strip()

    platform_type = record.get("platform_type")

    train_info = train_lookup.get(train_number)

    if train_info is None:

        train_type = "NOT_FOUND_IN_MASTER"

        unknown_train_master.append(
            train_number
        )

    else:

        train_type = (
            train_info.get("train_type")
            or train_info.get("type")
            or train_info.get("category")
            or train_info.get("service_type")
            or "UNKNOWN"
        )

    train_type = str(train_type).strip()

    train_type_counts[train_type] += 1

    platform_type_by_train_type[
        train_type
    ][platform_type] += 1

    # Keep a few examples
    if len(train_examples[train_type]) < 5:

        train_examples[train_type].append(
            {
                "train_number": train_number,
                "train_name": record.get("train_name"),
                "station_code": record.get("station_code"),
                "platform_number": record.get("platform_number"),
                "platform_type": platform_type,
            }
        )


# ============================================================
# OVERALL PLATFORM DISTRIBUTION
# ============================================================

platform_counts = Counter(
    record.get("platform_type")
    for record in timetable
)

print("\n")
print("=" * 70)
print("OVERALL PLATFORM DISTRIBUTION")
print("=" * 70)

for platform_type, count in platform_counts.items():

    print(
        f"{platform_type:<15} : {count}"
    )


# ============================================================
# TRAIN TYPE DISTRIBUTION
# ============================================================

print("\n")
print("=" * 70)
print("TRAIN TYPE DISTRIBUTION")
print("=" * 70)

for train_type, count in train_type_counts.most_common():

    print(
        f"{train_type:<30} : {count}"
    )


# ============================================================
# PLATFORM TYPE BY TRAIN TYPE
# ============================================================

print("\n")
print("=" * 70)
print("PLATFORM TYPE BY TRAIN TYPE")
print("=" * 70)

for train_type in sorted(
    platform_type_by_train_type
):

    print(
        f"\n{train_type}"
    )

    print("-" * 50)

    for platform_type, count in (
        platform_type_by_train_type[
            train_type
        ].items()
    ):

        print(
            f"  {platform_type:<20} : {count}"
        )


# ============================================================
# EXAMPLES
# ============================================================

print("\n")
print("=" * 70)
print("TRAIN TYPE EXAMPLES")
print("=" * 70)

for train_type in sorted(train_examples):

    print(
        f"\n[{train_type}]"
    )

    for example in train_examples[train_type]:

        print(
            f"  {example['train_number']} | "
            f"{example['train_name']} | "
            f"{example['station_code']} | "
            f"Platform {example['platform_number']} | "
            f"{example['platform_type']}"
        )


# ============================================================
# POSSIBLE SUBURBAN / LOCAL SERVICES
# ============================================================

suburban_keywords = [
    "LOCAL",
    "MEMU",
    "EMU",
    "SUBURBAN",
    "MEMU",
    "PASSENGER",
]


possible_small_trains = []

for train_type in train_type_counts:

    upper_type = train_type.upper()

    if any(
        keyword in upper_type
        for keyword in suburban_keywords
    ):

        possible_small_trains.append(
            train_type
        )


print("\n")
print("=" * 70)
print("POSSIBLE LOCAL / MEMU / SUBURBAN TYPES")
print("=" * 70)

if possible_small_trains:

    for train_type in possible_small_trains:

        print(
            f"{train_type:<30} : "
            f"{train_type_counts[train_type]} records"
        )

else:

    print(
        "No obvious LOCAL / MEMU / EMU / "
        "SUBURBAN train type found."
    )


# ============================================================
# CHECK POSSIBLE SMALL TRAINS
# ============================================================

print("\n")
print("=" * 70)
print("POSSIBLE SMALL TRAIN PLATFORM CHECK")
print("=" * 70)

small_records = []

for record in timetable:

    train_number = str(
        record.get("train_number", "")
    ).strip()

    train_info = train_lookup.get(
        train_number
    )

    if train_info is None:
        continue

    train_type = str(
        train_info.get("train_type")
        or train_info.get("type")
        or train_info.get("category")
        or train_info.get("service_type")
        or ""
    ).upper()

    if any(
        keyword in train_type
        for keyword in suburban_keywords
    ):

        small_records.append(
            record
        )


print(
    f"Possible Small-Train Records : "
    f"{len(small_records)}"
)

small_platform_counts = Counter(
    record.get("platform_type")
    for record in small_records
)

for platform_type, count in (
    small_platform_counts.items()
):

    print(
        f"  {platform_type:<20} : {count}"
    )


# ============================================================
# TRAIN MASTER MATCHING
# ============================================================

unique_project_trains = {
    str(record.get("train_number", "")).strip()
    for record in timetable
}

matched_trains = (
    unique_project_trains
    & set(train_lookup.keys())
)

unmatched_trains = (
    unique_project_trains
    - set(train_lookup.keys())
)

print("\n")
print("=" * 70)
print("TRAIN MASTER MATCHING")
print("=" * 70)

print(
    f"Unique Project Trains : "
    f"{len(unique_project_trains)}"
)

print(
    f"Matched With Master   : "
    f"{len(matched_trains)}"
)

print(
    f"Not In Train Master   : "
    f"{len(unmatched_trains)}"
)


# ============================================================
# FINAL INTERPRETATION
# ============================================================

print("\n")
print("=" * 70)
print("VERIFICATION SUMMARY")
print("=" * 70)

if len(small_records) == 0:

    print(
        "\nNo LOCAL / MEMU / EMU / SUBURBAN "
        "records were detected from the available "
        "train-master type information."
    )

    print(
        "\nThis does NOT automatically mean the "
        "timetable has no small trains."
    )

    print(
        "It may mean the train master uses a "
        "different classification field."
    )

elif all(
    record.get("platform_type") == "MAINLINE"
    for record in small_records
):

    print(
        "\nWARNING:"
    )

    print(
        "Possible LOCAL / MEMU / SUBURBAN trains "
        "are present, but all are currently "
        "classified as MAINLINE."
    )

    print(
        "\nThe platform allocation logic should "
        "be reviewed before modifying the final dataset."
    )

else:

    print(
        "\nSmall-train records have mixed platform "
        "classification."
    )

    print(
        "Further review is required to confirm "
        "whether the allocation rules are correct."
    )


print("\n")
print("=" * 70)
print("NO FILES WERE MODIFIED")
print("=" * 70)