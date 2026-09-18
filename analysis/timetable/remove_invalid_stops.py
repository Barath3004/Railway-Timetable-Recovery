import json
import os

# ==========================================================
# PATHS
# ==========================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "project_timetable_filtered.json"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "project_timetable_cleaned.json"
)

# ==========================================================
# LOAD DATA
# ==========================================================

print("=" * 70)
print("REMOVE INVALID STOPS")
print("=" * 70)

with open(INPUT_FILE, "r", encoding="utf-8") as file:
    timetable = json.load(file)

print(f"Loaded Records : {len(timetable):,}")

# ==========================================================
# HELPER
# ==========================================================

def is_missing(value):
    """
    Returns True if the value represents a missing field.
    """
    if value is None:
        return True

    value = str(value).strip().lower()

    return value in [
        "",
        "none",
        "null",
        "--",
        "na",
        "n/a"
    ]

# ==========================================================
# REMOVE INVALID STOPS
# ==========================================================

cleaned = []

removed = []

for row in timetable:

    arrival_missing = is_missing(row.get("arrival"))
    departure_missing = is_missing(row.get("departure"))

    # Remove only when BOTH are missing
    if arrival_missing and departure_missing:

        removed.append(row)

    else:

        cleaned.append(row)

# ==========================================================
# SAVE
# ==========================================================

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(
        cleaned,
        file,
        indent=4,
        ensure_ascii=False
    )

# ==========================================================
# SUMMARY
# ==========================================================

print()

print("=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"Original Records : {len(timetable):,}")
print(f"Removed Stops    : {len(removed):,}")
print(f"Remaining Records: {len(cleaned):,}")

print()

print("Saved To:")
print(OUTPUT_FILE)

print()

print("=" * 70)
print("REMOVE INVALID STOPS COMPLETED")
print("=" * 70)