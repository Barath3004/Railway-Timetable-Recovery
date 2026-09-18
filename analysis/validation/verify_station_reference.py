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
    "station",
    "station_reference.csv"
)

print("=" * 70)
print("VERIFY STATION REFERENCE")
print("=" * 70)

df = pd.read_csv(INPUT_FILE)

print(f"Loaded Stations : {len(df):,}")

print()

print("=" * 70)
print("COLUMN CHECK")
print("=" * 70)

print(df.columns.tolist())

print()

print("=" * 70)
print("MISSING VALUES")
print("=" * 70)

print(df.isnull().sum())

print()

print("=" * 70)
print("DUPLICATE STATION CODES")
print("=" * 70)

duplicates = df[df.duplicated("station_code")]

print(f"Duplicates : {len(duplicates)}")

if len(duplicates):

    print(duplicates[["station_code", "station_name"]])

print()

print("=" * 70)
print("DATA TYPES")
print("=" * 70)

print(df.dtypes)

print()

print("=" * 70)
print("PLATFORM STATISTICS")
print("=" * 70)

print(df["platforms_total"].describe())

print()

print("=" * 70)
print("VERIFICATION COMPLETED")
print("=" * 70)