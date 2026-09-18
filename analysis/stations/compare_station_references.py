import pandas as pd
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

OLD_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "station"
    / "station_reference.csv"
)

NEW_FILE = (
    PROJECT_ROOT
    / "data"
    / "master"
    / "station_wikipedia.csv"
)


# ============================================================
# LOAD FILES
# ============================================================

print("=" * 70)
print("STATION REFERENCE COMPARISON")
print("=" * 70)

print("\nLoading OLD station reference...")
old_df = pd.read_csv(OLD_FILE)

print(f"Old Records : {len(old_df)}")

print("\nLoading NEW Wikipedia station data...")
new_df = pd.read_csv(NEW_FILE)

print(f"New Records : {len(new_df)}")


# ============================================================
# NORMALIZE COLUMN NAMES
# ============================================================

# Old file:
# electrified
#
# New file:
# electrification_year
#
# Rename both internally to the same name for comparison.

if "electrified" in old_df.columns:
    old_df = old_df.rename(
        columns={
            "electrified": "electrification_year"
        }
    )

if "electrified" in new_df.columns:
    new_df = new_df.rename(
        columns={
            "electrified": "electrification_year"
        }
    )


# ============================================================
# NORMALIZE STATION CODES
# ============================================================

old_df["station_code"] = (
    old_df["station_code"]
    .astype(str)
    .str.strip()
    .str.upper()
)

new_df["station_code"] = (
    new_df["station_code"]
    .astype(str)
    .str.strip()
    .str.upper()
)


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

required_columns = [
    "station_code",
    "station_name",
    "railway_zone",
    "railway_division",
    "platforms_total",
    "mainline_platforms",
    "suburban_platforms",
    "electrification_year"
]

print("\n")
print("=" * 70)
print("COLUMN CHECK")
print("=" * 70)

print("OLD columns:")
print(old_df.columns.tolist())

print("\nNEW columns:")
print(new_df.columns.tolist())


old_missing = [
    col for col in required_columns
    if col not in old_df.columns
]

new_missing = [
    col for col in required_columns
    if col not in new_df.columns
]

if old_missing:
    print("\nMissing from OLD file:")
    print(old_missing)
    raise SystemExit("OLD file does not contain required columns.")

if new_missing:
    print("\nMissing from NEW file:")
    print(new_missing)
    raise SystemExit("NEW file does not contain required columns.")


# ============================================================
# STATION CODE SETS
# ============================================================

old_codes = set(old_df["station_code"])
new_codes = set(new_df["station_code"])


added_codes = sorted(new_codes - old_codes)
removed_codes = sorted(old_codes - new_codes)
common_codes = sorted(old_codes & new_codes)


# ============================================================
# BASIC SUMMARY
# ============================================================

print("\n")
print("=" * 70)
print("STATION COUNT COMPARISON")
print("=" * 70)

print(f"OLD stations       : {len(old_codes)}")
print(f"NEW stations       : {len(new_codes)}")
print(f"Common stations    : {len(common_codes)}")
print(f"Added stations     : {len(added_codes)}")
print(f"Removed stations   : {len(removed_codes)}")


# ============================================================
# ADDED STATIONS
# ============================================================

print("\n")
print("=" * 70)
print("ADDED STATIONS")
print("=" * 70)

if added_codes:

    added = (
        new_df[
            new_df["station_code"].isin(added_codes)
        ][required_columns]
    )

    print(
        added.to_string(index=False)
    )

else:
    print("None")


# ============================================================
# REMOVED STATIONS
# ============================================================

print("\n")
print("=" * 70)
print("REMOVED STATIONS")
print("=" * 70)

if removed_codes:

    removed = (
        old_df[
            old_df["station_code"].isin(removed_codes)
        ][
            [
                "station_code",
                "station_name"
            ]
        ]
    )

    print(
        removed.to_string(index=False)
    )

else:
    print("None")


# ============================================================
# COMMON STATIONS
# ============================================================

old_common = (
    old_df[
        old_df["station_code"].isin(common_codes)
    ]
    .set_index("station_code")
)

new_common = (
    new_df[
        new_df["station_code"].isin(common_codes)
    ]
    .set_index("station_code")
)


# ============================================================
# COLUMNS TO COMPARE
# ============================================================

columns_to_compare = [
    "station_name",
    "railway_zone",
    "railway_division",
    "platforms_total",
    "mainline_platforms",
    "suburban_platforms",
    "electrification_year"
]


# ============================================================
# COMPARE
# ============================================================

changed_records = []
unchanged_codes = []


for code in common_codes:

    changed_columns = []

    for column in columns_to_compare:

        old_value = old_common.loc[
            code,
            column
        ]

        new_value = new_common.loc[
            code,
            column
        ]

        # NaN vs NaN = unchanged
        if pd.isna(old_value) and pd.isna(new_value):
            continue

        old_str = str(old_value).strip()
        new_str = str(new_value).strip()

        if old_str != new_str:

            changed_columns.append(column)

    if changed_columns:

        changed_records.append(
            {
                "station_code": code,
                "changed_columns": ", ".join(
                    changed_columns
                )
            }
        )

    else:

        unchanged_codes.append(code)


# ============================================================
# CHANGED STATIONS
# ============================================================

print("\n")
print("=" * 70)
print("CHANGED EXISTING STATIONS")
print("=" * 70)

print(
    f"Changed : {len(changed_records)}"
)

if changed_records:

    changed_df = pd.DataFrame(
        changed_records
    )

    print(
        changed_df.to_string(index=False)
    )

else:
    print("None")


# ============================================================
# DETAILED FIELD CHANGES
# ============================================================

print("\n")
print("=" * 70)
print("DETAILED FIELD CHANGES")
print("=" * 70)


for record in changed_records:

    code = record["station_code"]

    print(f"\n--- {code} ---")

    for column in columns_to_compare:

        old_value = old_common.loc[
            code,
            column
        ]

        new_value = new_common.loc[
            code,
            column
        ]

        if pd.isna(old_value) and pd.isna(new_value):
            continue

        old_str = str(old_value).strip()
        new_str = str(new_value).strip()

        if old_str != new_str:

            print(f"{column}:")
            print(f"  OLD : {old_value}")
            print(f"  NEW : {new_value}")


# ============================================================
# UNCHANGED
# ============================================================

print("\n")
print("=" * 70)
print("UNCHANGED STATIONS")
print("=" * 70)

print(
    f"Unchanged : {len(unchanged_codes)}"
)

if unchanged_codes:

    print(
        ", ".join(unchanged_codes)
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n")
print("=" * 70)
print("COMPARISON COMPLETED")
print("=" * 70)

print(f"OLD stations       : {len(old_codes)}")
print(f"NEW stations       : {len(new_codes)}")
print(f"Common             : {len(common_codes)}")
print(f"Added              : {len(added_codes)}")
print(f"Removed            : {len(removed_codes)}")
print(f"Changed            : {len(changed_records)}")
print(f"Unchanged          : {len(unchanged_codes)}")

print("\nIMPORTANT:")
print("Neither CSV file was modified.")