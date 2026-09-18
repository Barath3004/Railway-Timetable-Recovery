import json
import os
from collections import defaultdict


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

RESOURCE_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "resource",
    "resource_allocation.json"
)

# Try both possible timetable locations
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


# ============================================================
# FIND TIMETABLE FILE
# ============================================================

TIMETABLE_FILE = None

for path in TIMETABLE_CANDIDATES:

    if os.path.exists(path):
        TIMETABLE_FILE = path
        break


if TIMETABLE_FILE is None:

    raise FileNotFoundError(
        "Could not find project_timetable_platform.json"
    )


print("=" * 80)
print("CONFLICT TRAIN INVESTIGATION")
print("=" * 80)
print()

print(
    f"Resource file : {RESOURCE_FILE}"
)

print(
    f"Timetable file: {TIMETABLE_FILE}"
)

print()


# ============================================================
# LOAD FILES
# ============================================================

with open(
    RESOURCE_FILE,
    "r",
    encoding="utf-8"
) as f:

    allocations = json.load(f)


with open(
    TIMETABLE_FILE,
    "r",
    encoding="utf-8"
) as f:

    timetable = json.load(f)


print(
    f"Resource allocations : {len(allocations)}"
)

print(
    f"Timetable records    : {len(timetable)}"
)


# ============================================================
# BUILD TIMETABLE LOOKUP
# ============================================================

timetable_lookup = {}

for record in timetable:

    record_id = record.get("id")

    if record_id is not None:

        timetable_lookup[
            str(record_id)
        ] = record


# ============================================================
# TIME HELPERS
# ============================================================

def time_to_minutes(value):

    if value is None:
        return None

    try:

        h, m, s = map(
            int,
            str(value).split(":")
        )

        return (
            h * 60
            + m
            + s / 60
        )

    except:

        return None


def absolute_minutes(day, value):

    minutes = time_to_minutes(value)

    if minutes is None:
        return None

    return (
        (int(day) - 1) * 1440
        + minutes
    )


def overlaps(a, b):

    return (
        a["start"] < b["end"]
        and b["start"] < a["end"]
    )


# ============================================================
# BUILD RESOURCE INTERVALS
# ============================================================

resource_groups = defaultdict(list)

for allocation in allocations:

    resource_id = allocation.get(
        "resource_id"
    )

    start = absolute_minutes(
        allocation.get("day"),
        allocation.get("allocation_start")
    )

    end = absolute_minutes(
        allocation.get("release_day"),
        allocation.get("release_time")
    )

    if (
        resource_id is None
        or start is None
        or end is None
    ):
        continue

    resource_groups[
        resource_id
    ].append(
        {
            "allocation": allocation,
            "start": start,
            "end": end
        }
    )


# ============================================================
# FIND CONFLICTS
# ============================================================

conflicts = []

for resource_id, records in resource_groups.items():

    records.sort(
        key=lambda x: (
            x["start"],
            x["end"]
        )
    )

    for i in range(len(records)):

        a = records[i]

        for j in range(
            i + 1,
            len(records)
        ):

            b = records[j]

            if b["start"] >= a["end"]:
                break

            if overlaps(a, b):

                conflicts.append(
                    {
                        "resource_id": resource_id,
                        "a": a["allocation"],
                        "b": b["allocation"]
                    }
                )


# ============================================================
# DUPLICATE / DIFFERENT TRAIN ANALYSIS
# ============================================================

print()
print("=" * 80)
print(
    f"FOUND {len(conflicts)} RESOURCE CONFLICTS"
)
print("=" * 80)


duplicate_candidates = []
different_trains = []
possible_duplicates = []


for index, conflict in enumerate(
    conflicts,
    start=1
):

    resource_id = conflict[
        "resource_id"
    ]

    allocation_a = conflict["a"]
    allocation_b = conflict["b"]

    id_a = str(
        allocation_a.get(
            "timetable_record_id"
        )
    )

    id_b = str(
        allocation_b.get(
            "timetable_record_id"
        )
    )

    train_a = timetable_lookup.get(
        id_a
    )

    train_b = timetable_lookup.get(
        id_b
    )

    print()
    print("-" * 80)
    print(
        f"CONFLICT #{index}"
    )
    print(
        f"RESOURCE: {resource_id}"
    )

    print()

    # --------------------------------------------------------
    # RECORD A
    # --------------------------------------------------------

    print("TRAIN A")
    print(
        f"  Timetable ID : {id_a}"
    )

    if train_a:

        print(
            f"  Train Number : "
            f"{train_a.get('train_number')}"
        )

        print(
            f"  Train Name   : "
            f"{train_a.get('train_name')}"
        )

        print(
            f"  Station      : "
            f"{train_a.get('station_code')} - "
            f"{train_a.get('station_name')}"
        )

        print(
            f"  Day          : "
            f"{train_a.get('day')}"
        )

        print(
            f"  Arrival      : "
            f"{train_a.get('arrival')}"
        )

        print(
            f"  Departure    : "
            f"{train_a.get('departure')}"
        )

        print(
            f"  Stop Number  : "
            f"{train_a.get('stop_number')}"
        )

        print(
            f"  Platform     : "
            f"{train_a.get('platform_number')}"
        )

    else:

        print(
            "  WARNING: Timetable record not found"
        )

    print()

    # --------------------------------------------------------
    # RECORD B
    # --------------------------------------------------------

    print("TRAIN B")
    print(
        f"  Timetable ID : {id_b}"
    )

    if train_b:

        print(
            f"  Train Number : "
            f"{train_b.get('train_number')}"
        )

        print(
            f"  Train Name   : "
            f"{train_b.get('train_name')}"
        )

        print(
            f"  Station      : "
            f"{train_b.get('station_code')} - "
            f"{train_b.get('station_name')}"
        )

        print(
            f"  Day          : "
            f"{train_b.get('day')}"
        )

        print(
            f"  Arrival      : "
            f"{train_b.get('arrival')}"
        )

        print(
            f"  Departure    : "
            f"{train_b.get('departure')}"
        )

        print(
            f"  Stop Number  : "
            f"{train_b.get('stop_number')}"
        )

        print(
            f"  Platform     : "
            f"{train_b.get('platform_number')}"
        )

    else:

        print(
            "  WARNING: Timetable record not found"
        )

    # --------------------------------------------------------
    # CLASSIFICATION
    # --------------------------------------------------------

    if train_a and train_b:

        number_a = str(
            train_a.get("train_number")
        ).strip()

        number_b = str(
            train_b.get("train_number")
        ).strip()

        name_a = str(
            train_a.get("train_name")
        ).strip().upper()

        name_b = str(
            train_b.get("train_name")
        ).strip().upper()

        station_a = train_a.get(
            "station_code"
        )

        station_b = train_b.get(
            "station_code"
        )

        day_a = train_a.get(
            "day"
        )

        day_b = train_b.get(
            "day"
        )

        arrival_a = train_a.get(
            "arrival"
        )

        arrival_b = train_b.get(
            "arrival"
        )

        departure_a = train_a.get(
            "departure"
        )

        departure_b = train_b.get(
            "departure"
        )

        same_train_number = (
            number_a == number_b
        )

        same_name = (
            name_a == name_b
        )

        same_station = (
            station_a == station_b
        )

        same_day = (
            day_a == day_b
        )

        same_arrival = (
            arrival_a == arrival_b
        )

        same_departure = (
            departure_a == departure_b
        )

        # ----------------------------------------------------
        # Strong duplicate candidate
        # ----------------------------------------------------

        if (
            same_train_number
            and same_name
            and same_station
            and same_day
            and same_arrival
            and same_departure
        ):

            classification = (
                "DUPLICATE CANDIDATE"
            )

            duplicate_candidates.append(
                conflict
            )

        # ----------------------------------------------------
        # Same train but something differs
        # ----------------------------------------------------

        elif same_train_number and same_name:

            classification = (
                "POSSIBLE DUPLICATE - "
                "SAME TRAIN BUT DETAILS DIFFER"
            )

            possible_duplicates.append(
                conflict
            )

        # ----------------------------------------------------
        # Different trains
        # ----------------------------------------------------

        else:

            classification = (
                "DIFFERENT TRAIN"
            )

            different_trains.append(
                conflict
            )

        print()
        print(
            f"CLASSIFICATION: {classification}"
        )

    else:

        print()
        print(
            "CLASSIFICATION: "
            "COULD NOT DETERMINE"
        )


# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print()
print("=" * 80)
print("FINAL CLASSIFICATION SUMMARY")
print("=" * 80)
print()

print(
    f"Total conflicts              : "
    f"{len(conflicts)}"
)

print(
    f"Duplicate candidates         : "
    f"{len(duplicate_candidates)}"
)

print(
    f"Possible duplicates          : "
    f"{len(possible_duplicates)}"
)

print(
    f"Different trains             : "
    f"{len(different_trains)}"
)


# ============================================================
# DUPLICATE CANDIDATES
# ============================================================

if duplicate_candidates:

    print()
    print("=" * 80)
    print("DUPLICATE CANDIDATES")
    print("=" * 80)

    for conflict in duplicate_candidates:

        a = conflict["a"]
        b = conflict["b"]

        id_a = str(
            a.get("timetable_record_id")
        )

        id_b = str(
            b.get("timetable_record_id")
        )

        train_a = timetable_lookup[id_a]

        print(
            f"{id_a} <-> {id_b} | "
            f"Train {train_a.get('train_number')} | "
            f"{train_a.get('station_code')} | "
            f"{train_a.get('arrival')} -> "
            f"{train_a.get('departure')}"
        )


# ============================================================
# DIFFERENT TRAIN SUMMARY
# ============================================================

if different_trains:

    print()
    print("=" * 80)
    print("DIFFERENT TRAIN CONFLICTS")
    print("=" * 80)

    for conflict in different_trains:

        a = conflict["a"]
        b = conflict["b"]

        train_a = timetable_lookup.get(
            str(
                a.get(
                    "timetable_record_id"
                )
            )
        )

        train_b = timetable_lookup.get(
            str(
                b.get(
                    "timetable_record_id"
                )
            )
        )

        if not train_a or not train_b:
            continue

        print(
            f"{conflict['resource_id']} | "
            f"{train_a.get('train_number')} "
            f"({train_a.get('id')}) "
            f"<-> "
            f"{train_b.get('train_number')} "
            f"({train_b.get('id')})"
        )


# ============================================================
# IMPORTANT
# ============================================================

print()
print("=" * 80)
print("IMPORTANT")
print("=" * 80)
print()

print(
    "NO FILES WERE MODIFIED."
)

print(
    "This script only investigates the conflicts."
)

print(
    "Do NOT delete any records based on this output yet."
)

print()
print("=" * 80)
print("DONE")
print("=" * 80)