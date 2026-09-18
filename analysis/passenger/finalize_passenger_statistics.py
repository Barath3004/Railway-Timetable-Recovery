import pandas as pd
import os

# ==========================================================
# PATHS
# ==========================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "passenger",
    "passenger_statistics.csv"
)

OUTPUT_FILE = INPUT_FILE

# ==========================================================
# LOAD
# ==========================================================

print("=" * 70)
print("FINALIZING PASSENGER STATISTICS")
print("=" * 70)

df = pd.read_csv(INPUT_FILE)

print(f"Loaded Records : {len(df):,}")

# ==========================================================
# REMOVE UNUSED COLUMN
# ==========================================================

if "old_category" in df.columns:

    df.drop(columns=["old_category"], inplace=True)

    print("Removed Column : old_category")

else:

    print("Column old_category not found.")

# ==========================================================
# SAVE
# ==========================================================

df.to_csv(
    OUTPUT_FILE,
    index=False
)

# ==========================================================
# SUMMARY
# ==========================================================

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"Total Records : {len(df):,}")
print(f"Total Columns : {len(df.columns)}")

print()

print("Final Columns:")

for column in df.columns:
    print(f"  - {column}")

print()

print("Saved To:")
print(OUTPUT_FILE)

print()
print("=" * 70)
print("PASSENGER STATISTICS FINALIZED")
print("=" * 70)