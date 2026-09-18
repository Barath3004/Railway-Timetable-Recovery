from pathlib import Path
import sqlite3
import pandas as pd


# ============================================================
# PROJECT PASSENGER DATASET BUILDER
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PASSENGER_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "passenger"
    / "passenger_statistics.csv"
)

DB_FILE = (
    PROJECT_ROOT
    / "data"
    / "database"
    / "railway_recovery.db"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "passenger"
    / "project_station_passenger_data.csv"
)


# ============================================================
# MANUAL DATA ALREADY VERIFIED / SELECTED
# ============================================================

MANUAL_DATA = {
    "KRR": {
        "station_name": "Karur Junction",
        "category": "NSG 4",
        "annual_passengers": None,
        "daily_passengers": 6258,
        "footfall": None,
        "passenger_data_source": "MANUAL_ESTIMATE",
    },

    "TPJ": {
        "station_name": "Tiruchchirappalli Junction",
        "category": "NSG 2",
        "annual_passengers": 7923000,
        "daily_passengers": round(7923000 / 365),
        "footfall": None,
        "passenger_data_source": "ANNUAL_CONVERTED",
    },

    "VM": {
        "station_name": "Villupuram Junction",
        "category": "NSG 3",
        "annual_passengers": 5400000,
        "daily_passengers": round(5400000 / 365),
        "footfall": None,
        "passenger_data_source": "MANUAL_ESTIMATE",
    },

    "VRI": {
        "station_name": "Vriddhachalam Junction",
        "category": "NSG 4",
        "annual_passengers": 2190000,
        "daily_passengers": round(2190000 / 365),
        "footfall": None,
        "passenger_data_source": "MANUAL_ESTIMATE",
    },

    "MAS": {
        "station_name": "Chennai Central Puratchi Thalaivar Dr. M.G. Ramachandran Central Railway Station",
        "category": "NSG 1",
        "annual_passengers": 54750000,
        "daily_passengers": 150000,
        "footfall": None,
        "passenger_data_source": "MANUAL_ESTIMATE",
    },

    "MS": {
        "station_name": "Chennai Egmore",
        "category": "NSG 1",
        "annual_passengers": 36500000,
        "daily_passengers": 100000,
        "footfall": None,
        "passenger_data_source": "MANUAL_ESTIMATE",
    },

    "TBM": {
        "station_name": "Tambaram",
        "category": "NSG 1",
        "annual_passengers": 43800000,
        "daily_passengers": 120000,
        "footfall": None,
        "passenger_data_source": "MANUAL_ESTIMATE",
    },

    "ABU": {
        "station_name": "Ambattur",
        "category": "SG 3",
        "annual_passengers": 4380000,
        "daily_passengers": 12000,
        "footfall": None,
        "passenger_data_source": "MANUAL_ESTIMATE",
    },

    "BBQ": {
        "station_name": "Basin Bridge Junction",
        "category": "SG 3",
        "annual_passengers": 2920000,
        "daily_passengers": 8000,
        "footfall": None,
        "passenger_data_source": "MANUAL_ESTIMATE",
    },

    "VLK": {
        "station_name": "Villivakkam",
        "category": "SG 3",
        "annual_passengers": 3650000,
        "daily_passengers": 10000,
        "footfall": None,
        "passenger_data_source": "MANUAL_ESTIMATE",
    },
}


# ============================================================
# LOAD SOURCE DATA
# ============================================================

print("=" * 60)
print("BUILDING PROJECT PASSENGER DATASET")
print("=" * 60)

df = pd.read_csv(PASSENGER_FILE)

print(f"\nSource records: {len(df)}")
print(f"Source columns: {len(df.columns)}")


# Convert numeric columns
numeric_columns = [
    "annual_passengers",
    "daily_passengers",
    "footfall",
]

for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")


# ============================================================
# GET AUTHORITATIVE PROJECT STATIONS FROM SQLITE
# ============================================================

conn = sqlite3.connect(DB_FILE)

project_stations = pd.read_sql_query(
    """
    SELECT
        station_code,
        station_name
    FROM stations
    ORDER BY station_code
    """,
    conn,
)

conn.close()

print(f"\nProject stations in SQLite: {len(project_stations)}")


# ============================================================
# MATCH SOURCE DATA
# ============================================================

project_codes = set(project_stations["station_code"])

matched = df[df["station_code"].isin(project_codes)].copy()

print(
    f"Passenger records matching project stations: {len(matched)}"
)


# ============================================================
# CATEGORY MEDIANS FROM SOURCE DATA
# ============================================================

category_stats = (
    df.dropna(subset=["daily_passengers"])
    .groupby("category")["daily_passengers"]
    .agg(
        count="count",
        median="median",
        mean="mean",
        minimum="min",
        maximum="max",
    )
    .reset_index()
)

print("\n" + "=" * 60)
print("CATEGORY PASSENGER STATISTICS")
print("=" * 60)

print(category_stats.to_string(index=False))


category_median = dict(
    zip(
        category_stats["category"],
        category_stats["median"],
    )
)


# ============================================================
# BUILD DATASET
# ============================================================

records = []
unresolved = []

for _, station in project_stations.iterrows():

    code = station["station_code"]
    db_name = station["station_name"]

    # --------------------------------------------------------
    # 1. MANUAL DATA
    # --------------------------------------------------------

    if code in MANUAL_DATA:

        item = MANUAL_DATA[code].copy()
        item["station_code"] = code

        if not item.get("station_name"):
            item["station_name"] = db_name

        records.append(item)
        continue

    # --------------------------------------------------------
    # 2. SOURCE DATA
    # --------------------------------------------------------

    source_rows = matched[
        matched["station_code"] == code
    ]

    if len(source_rows) == 0:

        unresolved.append(
            {
                "station_code": code,
                "station_name": db_name,
                "reason": "NO_SOURCE_RECORD",
            }
        )

        continue

    row = source_rows.iloc[0]

    category = row["category"]

    annual = row["annual_passengers"]
    daily = row["daily_passengers"]
    footfall = row["footfall"]

    # --------------------------------------------------------
    # 3. DAILY PASSENGERS AVAILABLE
    # --------------------------------------------------------

    if pd.notna(daily) and daily > 0:

        records.append(
            {
                "station_code": code,
                "station_name": db_name,
                "category": category,
                "annual_passengers": annual,
                "daily_passengers": round(daily),
                "footfall": footfall,
                "passenger_data_source": "DAILY_ACTUAL",
            }
        )

        continue

    # --------------------------------------------------------
    # 4. ANNUAL PASSENGERS AVAILABLE
    # --------------------------------------------------------

    if pd.notna(annual) and annual > 0:

        calculated_daily = round(annual / 365)

        records.append(
            {
                "station_code": code,
                "station_name": db_name,
                "category": category,
                "annual_passengers": annual,
                "daily_passengers": calculated_daily,
                "footfall": footfall,
                "passenger_data_source": "ANNUAL_CONVERTED",
            }
        )

        continue

    # --------------------------------------------------------
    # 5. CATEGORY-BASED ESTIMATE
    # --------------------------------------------------------

    if category in category_median:

        estimated_daily = round(category_median[category])

        records.append(
            {
                "station_code": code,
                "station_name": db_name,
                "category": category,
                "annual_passengers": None,
                "daily_passengers": estimated_daily,
                "footfall": footfall,
                "passenger_data_source": "CATEGORY_MEDIAN_ESTIMATE",
            }
        )

        continue

    # --------------------------------------------------------
    # 6. UNRESOLVED
    # --------------------------------------------------------

    unresolved.append(
        {
            "station_code": code,
            "station_name": db_name,
            "category": category,
            "reason": "NO_PASSENGER_DATA_AND_NO_CATEGORY_BASELINE",
        }
    )


# ============================================================
# RESULTS
# ============================================================

result = pd.DataFrame(records)

unresolved_df = pd.DataFrame(unresolved)


print("\n" + "=" * 60)
print("BUILD RESULT")
print("=" * 60)

print(f"\nResolved project stations: {len(result)}")
print(f"Unresolved project stations: {len(unresolved_df)}")


if len(result) > 0:

    print("\n=== PASSENGER DATA SOURCES ===")

    print(
        result["passenger_data_source"]
        .value_counts()
        .to_string()
    )


# ============================================================
# UNRESOLVED STATIONS
# ============================================================

if len(unresolved_df) > 0:

    print("\n" + "=" * 60)
    print("UNRESOLVED STATIONS")
    print("=" * 60)

    print(
        unresolved_df.to_string(index=False)
    )

else:

    print("\nAll project stations resolved.")


# ============================================================
# SAVE ONLY IF ALL 32 ARE RESOLVED
# ============================================================

if len(unresolved_df) == 0:

    # Ensure stable column order

    columns = [
        "station_code",
        "station_name",
        "category",
        "annual_passengers",
        "daily_passengers",
        "footfall",
        "passenger_data_source",
    ]

    result = result[columns]

    result.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print("\n" + "=" * 60)
    print("DATASET SAVED")
    print("=" * 60)

    print(f"\nOutput:")
    print(OUTPUT_FILE)

else:

    print("\nDataset NOT saved yet.")
    print("Resolve the unresolved stations first.")

print("\n" + "=" * 60)
print("PASSENGER DATASET BUILD COMPLETE")
print("=" * 60)