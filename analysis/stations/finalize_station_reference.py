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

OUTPUT_FILE = INPUT_FILE

print("=" * 70)
print("FINALIZING STATION REFERENCE")
print("=" * 70)

df = pd.read_csv(INPUT_FILE)

# ==========================================================
# Rename Column
# ==========================================================

df.rename(
    columns={
        "electrified": "electrification_year"
    },
    inplace=True
)

# ==========================================================
# Fill Missing Zone / Division
# ==========================================================

updates = {

    "BBQ": {
        "railway_zone": "Southern Railway",
        "railway_division": "Chennai"
    },

    "PER": {
        "railway_zone": "Southern Railway",
        "railway_division": "Chennai"
    },

    "VLK": {
        "railway_zone": "Southern Railway",
        "railway_division": "Chennai"
    },

    "ABU": {
        "railway_zone": "Southern Railway",
        "railway_division": "Chennai"
    },

    "AVD": {
        "railway_zone": "Southern Railway",
        "railway_division": "Chennai"
    },

    "TRL": {
        "railway_zone": "Southern Railway",
        "railway_division": "Chennai"
    },

    "KPD": {
        "railway_zone": "Southern Railway",
        "railway_division": "Chennai"
    },

    "JTJ": {
        "railway_zone": "Southern Railway",
        "railway_division": "Salem"
    },

    "VRI": {
        "railway_zone": "Southern Railway"
    },

    "KYJ": {
        "railway_zone": "Southern Railway",
        "railway_division": "Thiruvananthapuram"
    }

}

for code, values in updates.items():

    mask = df["station_code"] == code

    for column, value in values.items():

        df.loc[mask, column] = value

# ==========================================================
# Save
# ==========================================================

df.to_csv(
    OUTPUT_FILE,
    index=False
)

print()

print("=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"Stations : {len(df)}")

print()

print("Station Reference finalized successfully.")

print()

print("=" * 70)
print("COMPLETED")
print("=" * 70)