import json
from collections import defaultdict
from pathlib import Path
from datetime import datetime


# ============================================================
# CONFIG
# ============================================================

TIMETABLE_FILE = Path(
    "data/processed/project_timetable/project_timetable_platform.json"
)

RESOURCE_FILE = Path(
    "data/processed/resource/resource_allocation.json"
)

OUTPUT_FILE = Path(
    "analysis/resource_conflict_report.txt"
)

DETAIL_LIMIT = 100


# ============================================================
# HELPERS
# ============================================================

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_records(data):

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        for key in [
            "data",
            "records",
            "allocations",
            "resource_allocations",
            "timetable",
            "trains"
        ]:

            if key in data and isinstance(data[key], list):
                return data[key]

    raise ValueError("Could not find record list in JSON.")


def get_value(record, *keys):

    for key in keys:

        if key in record:
            return record[key]

    return None


def parse_time(value):

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        pass

    for fmt in [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%H:%M:%S",
        "%H:%M"
    ]:

        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass

    return None


# ============================================================
# LOAD
# ============================================================

print("Loading timetable...")

timetable_data = load_json(TIMETABLE_FILE)

print("Loading resource allocations...")

resource_data = load_json(RESOURCE_FILE)

timetable_records = extract_records(timetable_data)
resource_records = extract_records(resource_data)

print("Loaded.")


# ============================================================
# REPORT BUFFER
# ============================================================

report = []


def write(text=""):
    report.append(str(text))


# ============================================================
# BASIC INFORMATION
# ============================================================

write("=" * 80)
write("RAILWAY TIMETABLE / RESOURCE VALIDATION REPORT")
write("=" * 80)

write()
write("DATASET INFORMATION")
write("-" * 80)

write(f"Timetable records : {len(timetable_records)}")
write(f"Allocation records: {len(resource_records)}")


# ============================================================
# SAMPLE STRUCTURE
# ============================================================

write()
write("=" * 80)
write("TIMETABLE SAMPLE")
write("=" * 80)

if timetable_records:

    write(
        json.dumps(
            timetable_records[0],
            indent=2,
            ensure_ascii=False
        )
    )


write()
write("=" * 80)
write("RESOURCE ALLOCATION SAMPLE")
write("=" * 80)

if resource_records:

    write(
        json.dumps(
            resource_records[0],
            indent=2,
            ensure_ascii=False
        )
    )


# ============================================================
# TIMETABLE LOOKUP
# ============================================================

timetable_by_id = {}

for record in timetable_records:

    record_id = get_value(
        record,
        "id",
        "timetable_record_id"
    )

    if record_id is not None:

        timetable_by_id[str(record_id)] = record


# ============================================================
# RELATIONSHIP VALIDATION
# ============================================================

missing_links = []

for allocation in resource_records:

    timetable_id = get_value(
        allocation,
        "timetable_record_id"
    )

    if timetable_id is None:

        missing_links.append(
            allocation
        )

    elif str(timetable_id) not in timetable_by_id:

        missing_links.append(
            allocation
        )


write()
write("=" * 80)
write("RELATIONSHIP VALIDATION")
write("=" * 80)

write(
    f"Unique timetable IDs: {len(timetable_by_id)}"
)

write(
    f"Allocations with missing timetable reference: {len(missing_links)}"
)


# ============================================================
# RESOURCE STATISTICS
# ============================================================

resource_types = defaultdict(int)
resources = defaultdict(int)
stations = defaultdict(int)

for allocation in resource_records:

    resource_type = get_value(
        allocation,
        "resource_type"
    ) or "UNKNOWN"

    resource_id = get_value(
        allocation,
        "resource_id"
    ) or "UNKNOWN"

    station = get_value(
        allocation,
        "station_code"
    ) or "UNKNOWN"

    resource_types[str(resource_type)] += 1
    resources[str(resource_id)] += 1
    stations[str(station)] += 1


write()
write("=" * 80)
write("RESOURCE STATISTICS")
write("=" * 80)

write("Resource types:")

for key, value in sorted(
    resource_types.items()
):

    write(
        f"  {key}: {value}"
    )

write()
write(
    f"Unique physical resources: {len(resources)}"
)

write(
    f"Unique stations: {len(stations)}"
)


# ============================================================
# ZERO DURATION
# ============================================================

zero_duration = []

for allocation in resource_records:

    start = parse_time(
        allocation.get("allocation_start")
    )

    end = parse_time(
        allocation.get("allocation_end")
    )

    if start is not None and end is not None:

        if start == end:

            zero_duration.append(
                allocation
            )


write()
write("=" * 80)
write("ZERO-DURATION ALLOCATIONS")
write("=" * 80)

write(
    f"Total: {len(zero_duration)}"
)

for allocation in zero_duration[:20]:

    write(
        f"  allocation_id={allocation.get('allocation_id')} "
        f"resource={allocation.get('resource_id')} "
        f"time={allocation.get('allocation_start')} "
        f"timetable={allocation.get('timetable_record_id')}"
    )


# ============================================================
# INVALID INTERVALS
# ============================================================

invalid_intervals = []

for allocation in resource_records:

    start = parse_time(
        allocation.get("allocation_start")
    )

    end = parse_time(
        allocation.get("allocation_end")
    )

    if start is None or end is None:

        invalid_intervals.append(
            (
                allocation,
                "TIME_PARSE_ERROR"
            )
        )

    elif end < start:

        invalid_intervals.append(
            (
                allocation,
                "END_BEFORE_START"
            )
        )


write()
write("=" * 80)
write("INVALID TIME INTERVALS")
write("=" * 80)

write(
    f"Total: {len(invalid_intervals)}"
)

for allocation, reason in invalid_intervals[:20]:

    write(
        f"  {reason} | "
        f"allocation={allocation.get('allocation_id')} | "
        f"resource={allocation.get('resource_id')} | "
        f"start={allocation.get('allocation_start')} | "
        f"end={allocation.get('allocation_end')}"
    )


# ============================================================
# GROUP ALLOCATIONS BY RESOURCE
# ============================================================

allocations_by_resource = defaultdict(list)

for allocation in resource_records:

    resource_id = get_value(
        allocation,
        "resource_id"
    )

    if resource_id is None:
        continue

    start = parse_time(
        allocation.get("allocation_start")
    )

    end = parse_time(
        allocation.get("allocation_end")
    )

    if start is None or end is None:
        continue

    allocations_by_resource[
        str(resource_id)
    ].append(allocation)


# ============================================================
# CONFLICT DETECTION
# ============================================================

conflicts = []

for resource_id, allocations in allocations_by_resource.items():

    allocations.sort(
        key=lambda x: parse_time(
            x.get("allocation_start")
        )
    )

    for i in range(len(allocations)):

        current = allocations[i]

        current_start = parse_time(
            current.get("allocation_start")
        )

        current_end = parse_time(
            current.get("allocation_end")
        )

        for j in range(i + 1, len(allocations)):

            other = allocations[j]

            other_start = parse_time(
                other.get("allocation_start")
            )

            other_end = parse_time(
                other.get("allocation_end")
            )

            if other_start >= current_end:
                break

            if (
                current_start < other_end
                and other_start < current_end
            ):

                conflicts.append(
                    {
                        "resource_id": resource_id,
                        "a": current,
                        "b": other
                    }
                )


# ============================================================
# CONFLICT STATISTICS
# ============================================================

conflicts_by_resource = defaultdict(int)

for conflict in conflicts:

    conflicts_by_resource[
        conflict["resource_id"]
    ] += 1


write()
write("=" * 80)
write("RESOURCE CONFLICT ANALYSIS")
write("=" * 80)

write(
    f"Total overlapping allocation pairs: {len(conflicts)}"
)

write(
    f"Resources containing conflicts: {len(conflicts_by_resource)}"
)

write()
write("TOP CONFLICTING RESOURCES")

for resource_id, count in sorted(
    conflicts_by_resource.items(),
    key=lambda x: x[1],
    reverse=True
)[:30]:

    write(
        f"  {resource_id}: {count}"
    )


# ============================================================
# DETAILED CONFLICTS
# ============================================================

write()
write("=" * 80)
write(
    f"DETAILED CONFLICTS — FIRST {DETAIL_LIMIT}"
)
write("=" * 80)


for number, conflict in enumerate(
    conflicts[:DETAIL_LIMIT],
    start=1
):

    a = conflict["a"]
    b = conflict["b"]

    timetable_a = timetable_by_id.get(
        str(
            a.get("timetable_record_id")
        )
    )

    timetable_b = timetable_by_id.get(
        str(
            b.get("timetable_record_id")
        )
    )

    write()
    write("-" * 80)

    write(
        f"CONFLICT #{number}"
    )

    write(
        f"Resource ID: {conflict['resource_id']}"
    )

    write(
        f"Resource type: {a.get('resource_type')}"
    )

    write(
        f"Station: {a.get('station_code')} "
        f"({a.get('station_name')})"
    )

    write(
        f"Platform: {a.get('platform_number')}"
    )

    write()
    write("ALLOCATION A")

    write(
        f"  allocation_id: {a.get('allocation_id')}"
    )

    write(
        f"  timetable_record_id: "
        f"{a.get('timetable_record_id')}"
    )

    write(
        f"  allocation_start: "
        f"{a.get('allocation_start')}"
    )

    write(
        f"  allocation_end: "
        f"{a.get('allocation_end')}"
    )

    write(
        f"  occupancy_minutes: "
        f"{a.get('occupancy_minutes')}"
    )

    write(
        f"  buffer_minutes: "
        f"{a.get('buffer_minutes')}"
    )

    write(
        f"  release_time: "
        f"{a.get('release_time')}"
    )


    if timetable_a:

        write()
        write("  TIMETABLE A")

        for key, value in timetable_a.items():

            if any(
                word in key.lower()
                for word in [
                    "train",
                    "station",
                    "arrival",
                    "departure",
                    "platform",
                    "time",
                    "date",
                    "day"
                ]
            ):

                write(
                    f"    {key}: {value}"
                )


    write()
    write("ALLOCATION B")

    write(
        f"  allocation_id: {b.get('allocation_id')}"
    )

    write(
        f"  timetable_record_id: "
        f"{b.get('timetable_record_id')}"
    )

    write(
        f"  allocation_start: "
        f"{b.get('allocation_start')}"
    )

    write(
        f"  allocation_end: "
        f"{b.get('allocation_end')}"
    )

    write(
        f"  occupancy_minutes: "
        f"{b.get('occupancy_minutes')}"
    )

    write(
        f"  buffer_minutes: "
        f"{b.get('buffer_minutes')}"
    )

    write(
        f"  release_time: "
        f"{b.get('release_time')}"
    )


    if timetable_b:

        write()
        write("  TIMETABLE B")

        for key, value in timetable_b.items():

            if any(
                word in key.lower()
                for word in [
                    "train",
                    "station",
                    "arrival",
                    "departure",
                    "platform",
                    "time",
                    "date",
                    "day"
                ]
            ):

                write(
                    f"    {key}: {value}"
                )


# ============================================================
# SAME TIMETABLE → MULTIPLE ALLOCATIONS
# ============================================================

allocations_by_timetable = defaultdict(list)

for allocation in resource_records:

    timetable_id = allocation.get(
        "timetable_record_id"
    )

    allocations_by_timetable[
        str(timetable_id)
    ].append(allocation)


multiple_allocations = {
    key: value
    for key, value
    in allocations_by_timetable.items()
    if len(value) > 1
}


write()
write("=" * 80)
write("MULTIPLE ALLOCATIONS PER TIMETABLE RECORD")
write("=" * 80)

write(
    f"Timetable records with >1 allocation: "
    f"{len(multiple_allocations)}"
)


# ============================================================
# FINAL SUMMARY
# ============================================================

write()
write("=" * 80)
write("FINAL SUMMARY")
write("=" * 80)

write(
    f"Timetable records                  : {len(timetable_records)}"
)

write(
    f"Resource allocations               : {len(resource_records)}"
)

write(
    f"Missing timetable links             : {len(missing_links)}"
)

write(
    f"Zero-duration allocations           : {len(zero_duration)}"
)

write(
    f"Invalid time intervals              : {len(invalid_intervals)}"
)

write(
    f"Conflicting allocation pairs        : {len(conflicts)}"
)

write(
    f"Resources containing conflicts      : {len(conflicts_by_resource)}"
)

write(
    f"Timetable records with >1 allocation: "
    f"{len(multiple_allocations)}"
)

write()
write("END OF REPORT")


# ============================================================
# SAVE REPORT
# ============================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "\n".join(report)
    )


# ============================================================
# TERMINAL SUMMARY
# ============================================================

print()
print("=" * 60)
print("VALIDATION COMPLETE")
print("=" * 60)

print(
    f"Timetable records       : {len(timetable_records)}"
)

print(
    f"Allocation records      : {len(resource_records)}"
)

print(
    f"Missing timetable links : {len(missing_links)}"
)

print(
    f"Zero-duration records   : {len(zero_duration)}"
)

print(
    f"Invalid intervals       : {len(invalid_intervals)}"
)

print(
    f"Conflict pairs          : {len(conflicts)}"
)

print(
    f"Resources with conflicts: {len(conflicts_by_resource)}"
)

print()
print(
    f"FULL REPORT SAVED TO:"
)

print(
    OUTPUT_FILE.resolve()
)

print("=" * 60)