import pandas as pd
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TIMETABLE_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    /"project_timetable_platform_working.json"
)

STATION_REFERENCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "station"
    / "station_reference.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "station"
    / "candidate_station_ranking.csv"
)


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("RANKING CANDIDATE STATIONS")
print("=" * 70)

print("\nLoading timetable...")

timetable = pd.read_json(TIMETABLE_FILE)

print(f"Timetable Records : {len(timetable):,}")

print("\nLoading station reference...")

station_reference = pd.read_csv(STATION_REFERENCE_FILE)

print(f"Existing Stations : {len(station_reference)}")


# ============================================================
# IDENTIFY CURRENT 36 STATIONS
# ============================================================

existing_station_codes = set(
    station_reference["station_code"]
    .dropna()
    .astype(str)
    .str.strip()
    .str.upper()
)

print(f"Current Station Codes : {len(existing_station_codes)}")


# ============================================================
# NORMALIZE TIMETABLE STATION CODES
# ============================================================

timetable["station_code"] = (
    timetable["station_code"]
    .astype(str)
    .str.strip()
    .str.upper()
)


# ============================================================
# REMOVE INVALID / EMPTY CODES
# ============================================================

timetable = timetable[
    timetable["station_code"].notna()
    & (timetable["station_code"] != "")
    & (timetable["station_code"] != "NAN")
].copy()


# ============================================================
# FIND STATIONS OUTSIDE CURRENT 36
# ============================================================

candidate_timetable = timetable[
    ~timetable["station_code"].isin(existing_station_codes)
].copy()

print(
    f"Candidate Timetable Records : "
    f"{len(candidate_timetable):,}"
)


# ============================================================
# BASIC STATION FREQUENCY
# ============================================================

station_counts = (
    candidate_timetable
    .groupby("station_code")
    .size()
    .reset_index(name="timetable_records")
)


# ============================================================
# TRAIN COUNT
# ============================================================

if "train_number" in candidate_timetable.columns:

    train_counts = (
        candidate_timetable
        .groupby("station_code")["train_number"]
        .nunique()
        .reset_index(name="unique_trains")

    )

else:

    train_counts = pd.DataFrame(
        columns=["station_code", "unique_trains"]
    )


# ============================================================
# STATION NAME
# ============================================================

station_names = (
    candidate_timetable
    .groupby("station_code")["station_name"]
    .first()
    .reset_index()
)


# ============================================================
# JUNCTION / MAJOR STATION KEYWORDS
# ============================================================

candidate_data = station_counts.merge(
    train_counts,
    on="station_code",
    how="left"
)

candidate_data = candidate_data.merge(
    station_names,
    on="station_code",
    how="left"
)


candidate_data["station_name"] = (
    candidate_data["station_name"]
    .fillna("Unknown")
    .astype(str)
)


# ============================================================
# CLASSIFY STATION IMPORTANCE
# ============================================================

def classify_station(name):

    name_upper = name.upper()

    if "JUNCTION" in name_upper:
        return "Junction"

    if "JN" in name_upper.split():
        return "Junction"

    if "CENTRAL" in name_upper:
        return "Major"

    if "TERMINAL" in name_upper:
        return "Major"

    if "CANTONMENT" in name_upper:
        return "Major"

    return "Intermediate"


candidate_data["station_type"] = (
    candidate_data["station_name"]
    .apply(classify_station)
)


# ============================================================
# PASSENGER DATA CHECK
# ============================================================

PASSENGER_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "passenger"
    / "passenger_statistics.csv"
)

if PASSENGER_FILE.exists():

    passenger = pd.read_csv(PASSENGER_FILE)

    passenger["station_code"] = (
        passenger["station_code"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    passenger_codes = set(
        passenger["station_code"]
        .dropna()
    )

    candidate_data["passenger_data_available"] = (
        candidate_data["station_code"]
        .isin(passenger_codes)
    )

else:

    candidate_data["passenger_data_available"] = False


# ============================================================
# CALCULATE SCORE
# ============================================================

# Normalize timetable frequency
max_records = candidate_data["timetable_records"].max()

if max_records > 0:
    candidate_data["frequency_score"] = (
        candidate_data["timetable_records"]
        / max_records
        * 100
    )
else:
    candidate_data["frequency_score"] = 0


# Normalize unique train count
max_trains = candidate_data["unique_trains"].max()

if max_trains > 0:
    candidate_data["train_diversity_score"] = (
        candidate_data["unique_trains"]
        / max_trains
        * 100
    )
else:
    candidate_data["train_diversity_score"] = 0


# Station type score
candidate_data["station_type_score"] = (
    candidate_data["station_type"]
    .map(
        {
            "Junction": 100,
            "Major": 80,
            "Intermediate": 40
        }
    )
    .fillna(20)
)


# Passenger data score
candidate_data["passenger_score"] = (
    candidate_data["passenger_data_available"]
    .map(
        {
            True: 100,
            False: 0
        }
    )
)


# ============================================================
# FINAL WEIGHTED SCORE
# ============================================================

candidate_data["candidate_score"] = (
    candidate_data["frequency_score"] * 0.40
    + candidate_data["train_diversity_score"] * 0.25
    + candidate_data["station_type_score"] * 0.20
    + candidate_data["passenger_score"] * 0.15
)


# ============================================================
# SORT
# ============================================================

candidate_data = candidate_data.sort_values(
    by="candidate_score",
    ascending=False
).reset_index(drop=True)


candidate_data.insert(
    0,
    "rank",
    range(1, len(candidate_data) + 1)
)


# ============================================================
# DISPLAY TOP CANDIDATES
# ============================================================

print("\n")
print("=" * 70)
print("TOP CANDIDATE STATIONS")
print("=" * 70)

display_columns = [
    "rank",
    "station_code",
    "station_name",
    "station_type",
    "timetable_records",
    "unique_trains",
    "passenger_data_available",
    "candidate_score"
]

print(
    candidate_data[
        display_columns
    ]
    .head(30)
    .to_string(index=False)
)


# ============================================================
# SAVE RESULT
# ============================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

candidate_data.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("\n")
print("=" * 70)
print("RANKING COMPLETED")
print("=" * 70)

print(
    f"Existing Stations      : "
    f"{len(existing_station_codes)}"
)

print(
    f"Candidate Stations     : "
    f"{len(candidate_data)}"
)

print(
    f"Candidate Records      : "
    f"{len(candidate_timetable):,}"
)

print("\nTop 9 candidates:")

print(
    candidate_data[
        [
            "rank",
            "station_code",
            "station_name",
            "station_type",
            "timetable_records",
            "unique_trains",
            "passenger_data_available",
            "candidate_score"
        ]
    ]
    .head(9)
    .to_string(index=False)
)

print("\nSaved To:")
print(OUTPUT_FILE)

print("\nIMPORTANT:")
print(
    "This script only analyzes and ranks stations. "
    "It does NOT modify the timetable or station reference."
)