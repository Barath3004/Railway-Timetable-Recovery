import pandas as pd
import sqlite3

PASSENGER_FILE = "data/processed/passenger/passenger_statistics.csv"
DB_FILE = "data/database/railway_recovery.db"

# Load passenger data
passenger_df = pd.read_csv(PASSENGER_FILE)

# Get the authoritative project station list from SQLite
db = sqlite3.connect(DB_FILE)

project_stations = pd.read_sql_query("""
    SELECT station_code, station_name
    FROM stations
    ORDER BY station_code
""", db)

db.close()

# Match passenger data to project stations
matched = passenger_df[
    passenger_df["station_code"].isin(
        project_stations["station_code"]
    )
].copy()

print()
print("========================================")
print("     PROJECT PASSENGER DATA CHECK")
print("========================================")

print("Project stations in DB:", len(project_stations))
print("Passenger records:", len(passenger_df))
print("Matching passenger records:", len(matched))

print()
print("=== PROJECT STATIONS ===")

for _, station in project_stations.iterrows():
    code = station["station_code"]
    name = station["station_name"]

    matches = passenger_df[
        passenger_df["station_code"] == code
    ]

    if len(matches) > 0:
        print(
            f"{code:6} | {name:35} | "
            f"PASSENGER DATA FOUND ({len(matches)} record)"
        )
    else:
        print(
            f"{code:6} | {name:35} | "
            f"NO PASSENGER DATA"
        )

print()
print("=== MATCHED DATA ===")
print(
    matched[
        [
            "station_code",
            "station_name",
            "category",
            "annual_passengers",
            "daily_passengers",
            "footfall"
        ]
    ].to_string(index=False)
)

print()
print("========================================")
print("CHECK COMPLETE")
print("========================================")