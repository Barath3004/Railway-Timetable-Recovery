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

print("=" * 70)
print("VERIFY PASSENGER STATISTICS")
print("=" * 70)

df = pd.read_csv(INPUT_FILE)

print(f"Loaded Records : {len(df):,}")

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
    print(duplicates)

print()

print("=" * 70)
print("DATA TYPES")
print("=" * 70)

print(df.dtypes)

print()

print("=" * 70)
print("NUMERIC SUMMARY")
print("=" * 70)

print(df.describe(include="all"))

print()

print("=" * 70)
print("VERIFICATION COMPLETED")
print("=" * 70)