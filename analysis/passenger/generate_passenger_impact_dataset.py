import os
import json
import sqlite3
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import OrdinalEncoder


# ============================================================
# CONSTANTS & REPRODUCIBILITY
# ============================================================

SEED = 42
TOTAL_SCENARIOS = 50000

TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "database"
    / "railway_recovery.db"
)

PASSENGER_DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "passenger"
    / "project_station_passenger_data.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "passenger_ml"
)

PLOT_DIR = OUTPUT_DIR / "validation"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PLOT_DIR.mkdir(parents=True, exist_ok=True)

np.random.seed(SEED)


# ============================================================
# CHECK INPUT SOURCE DATA
# ============================================================

if not DB_PATH.exists():
    raise FileNotFoundError(
        f"Missing required SQLite database file: {DB_PATH}"
    )

if not PASSENGER_DATA_PATH.exists():
    raise FileNotFoundError(
        f"Missing required passenger baseline file: {PASSENGER_DATA_PATH}"
    )

print("=" * 70)
print("STARTING PASSENGER IMPACT SYNTHETIC DATASET GENERATION")
print("=" * 70)
print(f"Random Seed        : {SEED}")
print(f"Target Scenarios   : {TOTAL_SCENARIOS:,}")
print(f"Database Path      : {DB_PATH}")
print(f"Passenger File     : {PASSENGER_DATA_PATH}")
print(f"Output Directory   : {OUTPUT_DIR}")
print("=" * 70)


# ============================================================
# 1. LOAD AUTHORITATIVE DATABASE & PASSENGER DEMAND
# ============================================================

station_passenger_df = pd.read_csv(PASSENGER_DATA_PATH)

print(
    f"Loaded {len(station_passenger_df)} "
    f"project station passenger records."
)

conn = sqlite3.connect(DB_PATH)

trains_df = pd.read_sql_query(
    """
    SELECT
        train_number,
        train_name,
        train_type,
        priority
    FROM trains
    """,
    conn
)

timetable_df = pd.read_sql_query(
    """
    SELECT
        timetable_record_id,
        train_number,
        station_code,
        arrival,
        departure,
        day
    FROM timetable
    """,
    conn
)

stations_db_df = pd.read_sql_query(
    """
    SELECT
        station_code,
        station_name,
        platforms_total
    FROM stations
    """,
    conn
)

conn.close()

print(
    f"Loaded {len(trains_df)} trains, "
    f"{len(timetable_df)} timetable records, "
    f"{len(stations_db_df)} stations from DB."
)


# ============================================================
# 2. VALIDATE PASSENGER BASELINE
# ============================================================

required_passenger_columns = [
    "station_code",
    "station_name",
    "category",
    "daily_passengers",
    "passenger_data_source",
]

missing_passenger_columns = [
    col
    for col in required_passenger_columns
    if col not in station_passenger_df.columns
]

if missing_passenger_columns:
    raise ValueError(
        "Passenger baseline is missing required columns: "
        + ", ".join(missing_passenger_columns)
    )


# Use the authoritative 32 project stations from SQLite.

project_station_codes = list(
    stations_db_df["station_code"].dropna().unique()
)

station_passenger_df = station_passenger_df[
    station_passenger_df["station_code"].isin(project_station_codes)
].copy()

if len(station_passenger_df) != len(project_station_codes):
    missing_station_codes = sorted(
        set(project_station_codes)
        - set(station_passenger_df["station_code"])
    )

    raise ValueError(
        "Passenger baseline does not contain all project stations. "
        f"Missing: {missing_station_codes}"
    )


# Ensure passenger numbers are numeric.

station_passenger_df["daily_passengers"] = pd.to_numeric(
    station_passenger_df["daily_passengers"],
    errors="coerce"
)

if station_passenger_df["daily_passengers"].isna().any():
    missing_daily = station_passenger_df[
        station_passenger_df["daily_passengers"].isna()
    ]["station_code"].tolist()

    raise ValueError(
        "Daily passenger values are missing for: "
        + ", ".join(missing_daily)
    )

if (station_passenger_df["daily_passengers"] <= 0).any():
    invalid_daily = station_passenger_df[
        station_passenger_df["daily_passengers"] <= 0
    ]["station_code"].tolist()

    raise ValueError(
        "Daily passenger values must be greater than zero. "
        f"Invalid stations: {invalid_daily}"
    )


# ============================================================
# 3. MERGE TRAIN METADATA INTO TIMETABLE
# ============================================================

timetable_df = timetable_df.merge(
    trains_df,
    on="train_number",
    how="left"
)

timetable_df["train_type"] = timetable_df["train_type"].fillna(
    "Express"
)

timetable_df["priority"] = pd.to_numeric(
    timetable_df["priority"],
    errors="coerce"
).fillna(2).astype(int)


# ============================================================
# 4. LOOKUP DICTIONARIES
# ============================================================

station_demand_lookup = dict(
    zip(
        station_passenger_df["station_code"],
        station_passenger_df["daily_passengers"]
    )
)

station_name_lookup = dict(
    zip(
        station_passenger_df["station_code"],
        station_passenger_df["station_name"]
    )
)

station_category_lookup = dict(
    zip(
        station_passenger_df["station_code"],
        station_passenger_df["category"]
    )
)

station_source_lookup = dict(
    zip(
        station_passenger_df["station_code"],
        station_passenger_df["passenger_data_source"]
    )
)

station_codes = list(
    station_passenger_df["station_code"].unique()
)


# ============================================================
# 5. TIME-OF-DAY PROFILE
# ============================================================

# Raw period weights intentionally represent the desired
# relative passenger distribution.
#
# They are normalized automatically below so that the actual
# 24-hour total is EXACTLY 1.0.

RAW_TIME_PERIODS = [
    {
        "name": "Overnight",
        "start_hour": 0,
        "end_hour": 5,
        "raw_weight": 0.04,
        "hours": 6,
        "is_peak": 0,
    },
    {
        "name": "Morning build-up",
        "start_hour": 6,
        "end_hour": 8,
        "raw_weight": 0.14,
        "hours": 3,
        "is_peak": 0,
    },
    {
        "name": "Morning peak",
        "start_hour": 9,
        "end_hour": 11,
        "raw_weight": 0.22,
        "hours": 3,
        "is_peak": 1,
    },
    {
        "name": "Midday",
        "start_hour": 12,
        "end_hour": 15,
        "raw_weight": 0.14,
        "hours": 4,
        "is_peak": 0,
    },
    {
        "name": "Evening peak",
        "start_hour": 16,
        "end_hour": 18,
        "raw_weight": 0.24,
        "hours": 3,
        "is_peak": 1,
    },
    {
        "name": "Evening",
        "start_hour": 19,
        "end_hour": 21,
        "raw_weight": 0.14,
        "hours": 3,
        "is_peak": 0,
    },
    {
        "name": "Night",
        "start_hour": 22,
        "end_hour": 23,
        "raw_weight": 0.04,
        "hours": 2,
        "is_peak": 0,
    },
]

raw_weight_total = sum(
    tp["raw_weight"]
    for tp in RAW_TIME_PERIODS
)

TIME_PERIODS = []

for tp in RAW_TIME_PERIODS:

    normalized_weight = (
        tp["raw_weight"]
        / raw_weight_total
    )

    TIME_PERIODS.append(
        {
            "name": tp["name"],
            "start_hour": tp["start_hour"],
            "end_hour": tp["end_hour"],
            "period_weight": normalized_weight,
            "hours": tp["hours"],
            "is_peak": tp["is_peak"],
        }
    )

normalized_weight_total = sum(
    tp["period_weight"]
    for tp in TIME_PERIODS
)

if not math.isclose(
    normalized_weight_total,
    1.0,
    rel_tol=0.0,
    abs_tol=1e-12
):
    raise ValueError(
        f"Time-period weights do not sum to 1.0. "
        f"Actual sum: {normalized_weight_total}"
    )


def get_time_period_info(hour):
    """
    Return:
        period name
        peak flag
        hourly passenger weight
    """

    for tp in TIME_PERIODS:

        if (
            tp["start_hour"]
            <= hour
            <= tp["end_hour"]
        ):

            hourly_weight = (
                tp["period_weight"]
                / tp["hours"]
            )

            return (
                tp["name"],
                tp["is_peak"],
                hourly_weight,
            )

    raise ValueError(
        f"Hour {hour} does not belong to any time period."
    )


# ============================================================
# 6. TRAIN LOAD FACTORS
# ============================================================

LOAD_FACTOR_RANGES = {
    "EMU": (1.10, 1.60),
    "MEMU": (1.00, 1.45),
    "Passenger": (0.85, 1.25),
    "Express": (0.75, 1.15),
    "Mail": (0.75, 1.15),
    "Superfast": (0.70, 1.10),
    "Shatabdi": (0.70, 1.05),
    "Jan Shatabdi": (0.75, 1.10),
    "Duronto": (0.70, 1.05),
    "Rajdhani": (0.65, 1.00),
    "Garib Rath": (0.75, 1.10),
}


# Capacity ratio represents relative passenger carrying
# capability when estimating a train's share of station demand.

TRAIN_CAPACITY_RATIO = {
    "EMU": 1.50,
    "MEMU": 1.30,
    "Passenger": 1.10,
    "Express": 1.00,
    "Mail": 1.00,
    "Superfast": 0.95,
    "Shatabdi": 0.80,
    "Jan Shatabdi": 0.90,
    "Duronto": 0.85,
    "Rajdhani": 0.75,
    "Garib Rath": 0.95,
}


# ============================================================
# 7. DISRUPTION PARAMETERS
# ============================================================

DISRUPTION_TYPES = [
    "PLATFORM_CLOSURE",
    "TRACK_FAILURE",
    "SIGNAL_FAILURE",
    "PLANNED_MAINTENANCE",
    "OTHER_RESOURCE_DISRUPTION",
]

DISRUPTION_BASE_FACTOR = {
    "PLATFORM_CLOSURE": 0.90,
    "TRACK_FAILURE": 1.40,
    "SIGNAL_FAILURE": 1.15,
    "PLANNED_MAINTENANCE": 0.80,
    "OTHER_RESOURCE_DISRUPTION": 1.00,
}


DAYS_OF_WEEK = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


# ============================================================
# 8. DELAY DISTRIBUTION
# ============================================================

DELAY_BINS = [
    {
        "range": (1.0, 5.0),
        "prob": 0.20,
    },
    {
        "range": (5.0, 10.0),
        "prob": 0.25,
    },
    {
        "range": (10.0, 20.0),
        "prob": 0.25,
    },
    {
        "range": (20.0, 30.0),
        "prob": 0.15,
    },
    {
        "range": (30.0, 60.0),
        "prob": 0.10,
    },
    {
        "range": (60.0, 120.0),
        "prob": 0.05,
    },
]

DELAY_PROBS = [
    b["prob"]
    for b in DELAY_BINS
]

if not math.isclose(
    sum(DELAY_PROBS),
    1.0,
    rel_tol=0.0,
    abs_tol=1e-12
):
    raise ValueError(
        "Delay probabilities must sum to 1.0."
    )


# ============================================================
# 9. TIME UTILITIES
# ============================================================

def parse_time_to_minutes(value):
    """
    Convert HH:MM or HH:MM:SS into minutes after midnight.
    """

    if value is None:
        return None

    if pd.isna(value):
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        parts = text.split(":")

        hour = int(parts[0])
        minute = int(parts[1])

        if not (0 <= hour <= 23):
            return None

        if not (0 <= minute <= 59):
            return None

        return hour * 60 + minute

    except (
        ValueError,
        IndexError
    ):
        return None


def circular_time_distance(a, b):
    """
    Minimum distance between two times on a 24-hour clock.
    """

    diff = abs(a - b)

    return min(
        diff,
        1440 - diff
    )


def interval_contains_time(
    start_minute,
    end_minute,
    target_minute
):
    """
    Determine whether target_minute lies inside a timetable
    interval, including cross-midnight intervals.
    """

    if (
        start_minute is None
        or end_minute is None
    ):
        return False

    if start_minute == end_minute:
        return target_minute == start_minute

    if end_minute > start_minute:

        return (
            start_minute
            <= target_minute
            <= end_minute
        )

    # Cross-midnight interval.

    return (
        target_minute >= start_minute
        or target_minute <= end_minute
    )


def interval_overlaps_window(
    start_minute,
    end_minute,
    window_start,
    window_end
):
    """
    Determine whether a timetable interval overlaps a scenario
    disruption window.

    Supports cross-midnight intervals and disruption windows.
    """

    if (
        start_minute is None
        or end_minute is None
    ):
        return False

    def expand_interval(
        start,
        end
    ):

        if end >= start:
            return [
                (start, end)
            ]

        return [
            (start, 1440),
            (0, end),
        ]

    intervals_a = expand_interval(
        start_minute,
        end_minute
    )

    intervals_b = expand_interval(
        window_start,
        window_end
    )

    for (
        a_start,
        a_end
    ) in intervals_a:

        for (
            b_start,
            b_end
        ) in intervals_b:

            if (
                a_start <= b_end
                and b_start <= a_end
            ):
                return True

    return False


# ============================================================
# 10. PREPARE TIMETABLE RECORDS
# ============================================================

print(
    "\nPreparing timetable time information..."
)

timetable_df["arrival_minutes"] = timetable_df[
    "arrival"
].apply(
    parse_time_to_minutes
)

timetable_df["departure_minutes"] = timetable_df[
    "departure"
].apply(
    parse_time_to_minutes
)

timetable_df["day"] = pd.to_numeric(
    timetable_df["day"],
    errors="coerce"
).fillna(1).astype(int)

timetable_df["day"] = timetable_df[
    "day"
].clip(
    lower=1,
    upper=7
)


# ============================================================
# 11. INDEX TIMETABLE BY STATION
# ============================================================

print(
    "Building station timetable index..."
)

timetable_by_station = {}

for station_code in station_codes:

    station_records = timetable_df[
        timetable_df["station_code"]
        == station_code
    ].copy()

    timetable_by_station[
        station_code
    ] = station_records.to_dict(
        "records"
    )


# ============================================================
# 12. HELPER: FIND TIME-RELEVANT TRAIN SERVICES
# ============================================================

def get_time_relevant_records(
    station_records,
    scenario_time,
    disruption_duration
):
    """
    Select timetable services that are operationally relevant
    to the generated scenario time.

    Priority:
    1. Services active at scenario time.
    2. Services overlapping the disruption window.
    3. Services close to the scenario time.

    This prevents arbitrary train selection unrelated to
    the disruption time.
    """

    if not station_records:
        return []

    active_records = []

    disruption_end_time = (
        scenario_time
        + int(
            round(
                disruption_duration
            )
        )
    ) % 1440

    for rec in station_records:

        arrival = rec.get(
            "arrival_minutes"
        )

        departure = rec.get(
            "departure_minutes"
        )

        if (
            arrival is None
            and departure is None
        ):
            continue

        if arrival is None:
            arrival = departure

        if departure is None:
            departure = arrival

        # Scenario time directly intersects service.

        if interval_contains_time(
            arrival,
            departure,
            scenario_time
        ):

            active_records.append(
                rec
            )

            continue

        # Service interval overlaps disruption window.

        if interval_overlaps_window(
            arrival,
            departure,
            scenario_time,
            disruption_end_time
        ):

            active_records.append(
                rec
            )

    if active_records:
        return active_records

    # Fallback: select services closest to scenario time.

    candidates = []

    for rec in station_records:

        arrival = rec.get(
            "arrival_minutes"
        )

        departure = rec.get(
            "departure_minutes"
        )

        if (
            arrival is None
            and departure is None
        ):
            continue

        reference_time = (
            departure
            if departure is not None
            else arrival
        )

        distance = circular_time_distance(
            reference_time,
            scenario_time
        )

        candidates.append(
            (
                distance,
                rec
            )
        )

    candidates.sort(
        key=lambda x: x[0]
    )

    # Keep services within 120 minutes where possible.

    nearby = [
        rec
        for distance, rec in candidates
        if distance <= 120
    ]

    if nearby:
        return nearby[:25]

    return [
        rec
        for _, rec in candidates[:10]
    ]


# ============================================================
# 13. HELPER: CALCULATE TRAIN SERVICE SHARE
# ============================================================

def calculate_train_service_share(
    relevant_records,
    selected_train_type
):
    """
    Estimate the selected train's passenger-demand share using
    actual timetable services around the scenario time.

    Each train service receives a capacity-weighted share.

    The denominator is the total relative capacity of services
    operating around the scenario time.
    """

    if not relevant_records:
        return 0.10

    capacity_values = []

    for rec in relevant_records:

        train_type = rec.get(
            "train_type",
            "Express"
        )

        capacity_ratio = TRAIN_CAPACITY_RATIO.get(
            train_type,
            1.0
        )

        capacity_values.append(
            float(
                capacity_ratio
            )
        )

    total_capacity = sum(
        capacity_values
    )

    if total_capacity <= 0:
        return 0.10

    selected_capacity = TRAIN_CAPACITY_RATIO.get(
        selected_train_type,
        1.0
    )

    share = (
        selected_capacity
        / total_capacity
    )

    # Keep the synthetic model bounded.

    share = float(
        np.clip(
            share,
            0.05,
            0.50
        )
    )

    return share


# ============================================================
# 14. STATION SAMPLING
# ============================================================

station_passengers_array = np.array(
    [
        station_demand_lookup[sc]
        for sc in station_codes
    ],
    dtype=float
)

station_sampling_probs = (
    station_passengers_array
    / station_passengers_array.sum()
)

# Blend 50% uniform and 50% passenger-demand weighted
# sampling so smaller stations remain represented.

station_sampling_probs = (
    0.5
    * (
        1.0
        / len(station_codes)
    )
    + 0.5
    * station_sampling_probs
)

station_sampling_probs = (
    station_sampling_probs
    / station_sampling_probs.sum()
)


# ============================================================
# 15. TIME SAMPLING
# ============================================================

hour_probabilities = np.zeros(
    24,
    dtype=float
)

for tp in TIME_PERIODS:

    hourly_weight = (
        tp["period_weight"]
        / tp["hours"]
    )

    for hour in range(
        tp["start_hour"],
        tp["end_hour"] + 1
    ):

        hour_probabilities[
            hour
        ] = hourly_weight


if not math.isclose(
    hour_probabilities.sum(),
    1.0,
    rel_tol=0.0,
    abs_tol=1e-12
):
    raise ValueError(
        "Hourly probabilities do not sum to 1.0."
    )


# ============================================================
# 16. GENERATION LOOP
# ============================================================

print(
    "\nGenerating "
    f"{TOTAL_SCENARIOS:,} synthetic passenger "
    "impact scenarios..."
)

rows = []

used_scenarios = set()

generation_attempts = 0

max_generation_attempts = (
    TOTAL_SCENARIOS
    * 20
)


while len(rows) < TOTAL_SCENARIOS:

    generation_attempts += 1

    if (
        generation_attempts
        > max_generation_attempts
    ):

        raise RuntimeError(
            "Generation stopped because too many attempts "
            "were required to create unique scenarios."
        )

    # --------------------------------------------------------
    # A. Station
    # --------------------------------------------------------

    st_idx = np.random.choice(
        len(station_codes),
        p=station_sampling_probs
    )

    station_code = station_codes[
        st_idx
    ]

    station_name = station_name_lookup[
        station_code
    ]

    station_category = station_category_lookup[
        station_code
    ]

    daily_passengers = float(
        station_demand_lookup[
            station_code
        ]
    )

    passenger_source = station_source_lookup[
        station_code
    ]

    # --------------------------------------------------------
    # B. Day
    # --------------------------------------------------------

    day_idx = np.random.randint(
        0,
        7
    )

    day_of_week = DAYS_OF_WEEK[
        day_idx
    ]

    timetable_day = (
        day_idx
        + 1
    )

    day_type = (
        "Weekend"
        if day_of_week
        in [
            "Saturday",
            "Sunday"
        ]
        else "Weekday"
    )

    # --------------------------------------------------------
    # C. Time
    # --------------------------------------------------------

    hour = int(
        np.random.choice(
            24,
            p=hour_probabilities
        )
    )

    minute = int(
        np.random.randint(
            0,
            60
        )
    )

    time_str = (
        f"{hour:02d}:{minute:02d}"
    )

    (
        time_period,
        is_peak,
        hourly_time_weight,
    ) = get_time_period_info(
        hour
    )

    # Station demand during this hour.

    time_dependent_demand = (
        daily_passengers
        * hourly_time_weight
    )

    # Weekend adjustment.

    if day_type == "Weekend":
        time_dependent_demand *= 0.85

    # --------------------------------------------------------
    # D. Timetable-grounded train selection
    # --------------------------------------------------------

    station_records = (
        timetable_by_station[
            station_code
        ]
    )

    # --------------------------------------------------------
    # E. Disruption parameters needed to identify relevant
    #    timetable services.
    # --------------------------------------------------------

    disruption_type = np.random.choice(
        DISRUPTION_TYPES
    )

    disruption_duration = float(
        np.random.gamma(
            shape=3.0,
            scale=15.0
        )
        + 10.0
    )

    disruption_duration = float(
        np.clip(
            disruption_duration,
            10.0,
            180.0
        )
    )

    # Relevant train services around scenario time.

    relevant_records = get_time_relevant_records(
        station_records,
        hour * 60 + minute,
        disruption_duration
    )

    if not relevant_records:
        # Station may have no usable timetable service.
        # Try another station/time combination.

        continue

    # Restrict candidate trains to the correct timetable day
    # when day information is available.

    day_records = [
        rec
        for rec in relevant_records
        if int(
            rec.get(
                "day",
                timetable_day
            )
        ) == timetable_day
    ]

    if day_records:
        relevant_records = day_records

    # Select a service from the time-relevant timetable.

    tt_rec = relevant_records[
        np.random.randint(
            0,
            len(relevant_records)
        )
    ]

    train_number = str(
        tt_rec[
            "train_number"
        ]
    )

    train_type = (
        tt_rec.get(
            "train_type",
            "Express"
        )
        if pd.notna(
            tt_rec.get(
                "train_type",
                "Express"
            )
        )
        else "Express"
    )

    priority_value = tt_rec.get(
        "priority",
        2
    )

    try:

        train_priority = int(
            priority_value
        )

    except (
        ValueError,
        TypeError
    ):

        train_priority = 2

    # --------------------------------------------------------
    # F. Train load factor
    # --------------------------------------------------------

    lf_min, lf_max = LOAD_FACTOR_RANGES.get(
        train_type,
        (0.75, 1.15)
    )

    train_load_factor = float(
        np.random.uniform(
            lf_min,
            lf_max
        )
    )

    # --------------------------------------------------------
    # G. Actual timetable-based service share
    # --------------------------------------------------------

    train_service_share = (
        calculate_train_service_share(
            relevant_records,
            train_type
        )
    )

    # --------------------------------------------------------
    # H. Base train passenger exposure
    # --------------------------------------------------------

    train_passenger_exposure = (
        time_dependent_demand
        * train_service_share
        * train_load_factor
    )

    # --------------------------------------------------------
    # I. Disruption start/end
    # --------------------------------------------------------

    start_total_mins = (
        hour * 60
        + minute
    )

    end_total_mins = (
        start_total_mins
        + int(
            round(
                disruption_duration
            )
        )
    ) % 1440

    disruption_start = (
        f"{start_total_mins // 60:02d}:"
        f"{start_total_mins % 60:02d}"
    )

    disruption_end = (
        f"{end_total_mins // 60:02d}:"
        f"{end_total_mins % 60:02d}"
    )

    # --------------------------------------------------------
    # J. Affected train count
    # --------------------------------------------------------

    # The count grows with disruption duration and station
    # demand, but remains bounded.

    demand_scale = max(
        1.0,
        daily_passengers / 2000.0
    )

    base_affected = max(
        1,
        int(
            round(
                disruption_duration
                / 25.0
                * (
                    1.0
                    + math.log10(
                        demand_scale
                    )
                )
            )
        )
    )

    affected_train_count = int(
        np.clip(
            base_affected
            + np.random.randint(
                -1,
                3
            ),
            1,
            18
        )
    )

    # --------------------------------------------------------
    # K. Delay duration
    # --------------------------------------------------------

    bin_idx = np.random.choice(
        len(DELAY_BINS),
        p=DELAY_PROBS
    )

    d_min, d_max = (
        DELAY_BINS[
            bin_idx
        ]["range"]
    )

    delay_minutes = float(
        np.random.uniform(
            d_min,
            d_max
        )
    )

    # --------------------------------------------------------
    # L. Disruption exposure factor
    # --------------------------------------------------------

    # IMPORTANT:
    #
    # The disruption type factor is applied HERE.
    #
    # It is NOT applied again in severity_factor.
    #
    # This prevents double-counting the disruption type.

    base_type_factor = (
        DISRUPTION_BASE_FACTOR[
            disruption_type
        ]
    )

    train_count_factor = float(
        np.clip(
            1.0
            + 0.05
            * (
                affected_train_count
                - 1
            ),
            1.0,
            2.5
        )
    )

    duration_factor = float(
        np.clip(
            (
                1.0
                + disruption_duration
                / 120.0
            ) ** 0.5,
            1.0,
            2.0
        )
    )

    disruption_exposure_factor = (
        base_type_factor
        * train_count_factor
        * duration_factor
    )

    # --------------------------------------------------------
    # M. Severity factor
    # --------------------------------------------------------

    # IMPORTANT:
    #
    # BaseTypeFactor has deliberately been removed.
    #
    # Disruption type is already represented by
    # disruption_exposure_factor.
    #
    # Severity now represents contextual passenger consequence:
    #
    #   Peak period
    #   +
    #   Train priority
    #
    # This prevents the disruption type from being applied twice.

    peak_multiplier = (
        1.25
        if is_peak == 1
        else 1.0
    )

    priority_multiplier = (
        1.20
        if train_priority == 1
        else (
            1.10
            if train_priority == 2
            else 1.0
        )
    )

    severity_factor = (
        peak_multiplier
        * priority_multiplier
    )

    # --------------------------------------------------------
    # N. Target calculation
    # --------------------------------------------------------

    affected_passengers_raw = (
        train_passenger_exposure
        * disruption_exposure_factor
    )

    passenger_delay_raw = (
        affected_passengers_raw
        * delay_minutes
        * severity_factor
    )

    # --------------------------------------------------------
    # O. Controlled noise
    # --------------------------------------------------------

    noise = float(
        np.random.uniform(
            -0.10,
            0.10
        )
    )

    affected_passengers = max(
        1,
        int(
            round(
                affected_passengers_raw
                * (
                    1.0
                    + noise
                )
            )
        )
    )

    passenger_delay_minutes = max(
        0.1,
        round(
            passenger_delay_raw
            * (
                1.0
                + noise
            ),
            2
        )
    )

    # --------------------------------------------------------
    # P. Duplicate scenario prevention
    # --------------------------------------------------------

    dedup_key = (
        station_code,
        timetable_day,
        time_str,
        train_number,
        disruption_type,
        int(
            round(
                delay_minutes
            )
        ),
        int(
            round(
                disruption_duration
            )
        ),
    )

    if dedup_key in used_scenarios:
        continue

    used_scenarios.add(
        dedup_key
    )

    scenario_id = (
        f"SCN_{len(rows) + 1:05d}"
    )

    # --------------------------------------------------------
    # Q. Store scenario
    # --------------------------------------------------------

    row = {
        "scenario_id": scenario_id,

        "station_code": station_code,
        "station_name": station_name,
        "station_category": station_category,
        "station_daily_passengers": daily_passengers,
        "passenger_data_source": passenger_source,

        "day_of_week": day_of_week,
        "day_type": day_type,

        "time": time_str,
        "hour": hour,
        "minute": minute,
        "time_period": time_period,
        "is_peak_period": is_peak,

        "train_number": train_number,
        "train_type": train_type,
        "train_priority": train_priority,

        "disruption_type": disruption_type,
        "disruption_start": disruption_start,
        "disruption_end": disruption_end,
        "disruption_duration_minutes": round(
            disruption_duration,
            1
        ),

        "delay_minutes": round(
            delay_minutes,
            1
        ),

        "affected_train_count": (
            affected_train_count
        ),

        "train_service_share": round(
            train_service_share,
            5
        ),

        "train_load_factor": round(
            train_load_factor,
            4
        ),

        "train_passenger_exposure": round(
            train_passenger_exposure,
            2
        ),

        "affected_passengers": (
            affected_passengers
        ),

        "passenger_delay_minutes": (
            passenger_delay_minutes
        ),

        "severity_factor": round(
            severity_factor,
            3
        ),

        "disruption_exposure_factor": round(
            disruption_exposure_factor,
            3
        ),

        "controlled_noise": round(
            noise,
            5
        ),
    }

    rows.append(
        row
    )

    if len(rows) % 5000 == 0:

        print(
            f"Generated {len(rows):,} / "
            f"{TOTAL_SCENARIOS:,} scenarios..."
        )


# ============================================================
# 17. CREATE DATAFRAME
# ============================================================

dataset_df = pd.DataFrame(
    rows
)

print(
    f"\nSuccessfully generated "
    f"{len(dataset_df):,} synthetic scenarios."
)


# ============================================================
# 18. SAVE COMPLETE DATASET
# ============================================================

dataset_path = (
    OUTPUT_DIR
    / "passenger_impact_synthetic_dataset.csv"
)

dataset_df.to_csv(
    dataset_path,
    index=False
)

print(
    f"Saved full synthetic dataset to: "
    f"{dataset_path}"
)


# ============================================================
# 19. TRAIN / VALIDATION / TEST SPLIT
# ============================================================

print(
    "\nPerforming reproducible "
    "Train (70%) / Validation (15%) / "
    "Test (15%) split..."
)

np.random.seed(
    SEED
)

shuffled_indices = np.random.permutation(
    len(dataset_df)
)

train_cutoff = int(
    TOTAL_SCENARIOS
    * TRAIN_RATIO
)

val_cutoff = int(
    TOTAL_SCENARIOS
    * (
        TRAIN_RATIO
        + VAL_RATIO
    )
)

train_idx = shuffled_indices[
    :train_cutoff
]

val_idx = shuffled_indices[
    train_cutoff:val_cutoff
]

test_idx = shuffled_indices[
    val_cutoff:
]

train_df = (
    dataset_df
    .iloc[train_idx]
    .copy()
    .reset_index(drop=True)
)

val_df = (
    dataset_df
    .iloc[val_idx]
    .copy()
    .reset_index(drop=True)
)

test_df = (
    dataset_df
    .iloc[test_idx]
    .copy()
    .reset_index(drop=True)
)

train_csv_path = (
    OUTPUT_DIR
    / "train.csv"
)

val_csv_path = (
    OUTPUT_DIR
    / "validation.csv"
)

test_csv_path = (
    OUTPUT_DIR
    / "test.csv"
)

train_df.to_csv(
    train_csv_path,
    index=False
)

val_df.to_csv(
    val_csv_path,
    index=False
)

test_df.to_csv(
    test_csv_path,
    index=False
)

print(
    f"Train set      : {len(train_df):,} rows "
    f"({len(train_df) / len(dataset_df) * 100:.1f}%)"
)

print(
    f"Validation set : {len(val_df):,} rows "
    f"({len(val_df) / len(dataset_df) * 100:.1f}%)"
)

print(
    f"Test set       : {len(test_df):,} rows "
    f"({len(test_df) / len(dataset_df) * 100:.1f}%)"
)


# ============================================================
# 20. DATA VALIDATION
# ============================================================

print(
    "\nPerforming Data Quality & Statistical "
    "Validation Checks..."
)


# ------------------------------------------------------------
# Check A: Row counts
# ------------------------------------------------------------

total_rows = len(
    dataset_df
)

train_rows = len(
    train_df
)

val_rows = len(
    val_df
)

test_rows = len(
    test_df
)

pass_row_counts = (
    total_rows == TOTAL_SCENARIOS
    and
    train_rows
    + val_rows
    + test_rows
    == total_rows
)


# ------------------------------------------------------------
# Check B: Missing values
# ------------------------------------------------------------

missing_counts = (
    dataset_df
    .isna()
    .sum()
    .to_dict()
)

total_missing = sum(
    missing_counts.values()
)

pass_missing = (
    total_missing == 0
)


# ------------------------------------------------------------
# Check C: Duplicate scenario IDs
# ------------------------------------------------------------

duplicate_scenarios = (
    dataset_df[
        "scenario_id"
    ]
    .duplicated()
    .sum()
)

pass_duplicates = (
    duplicate_scenarios == 0
)


# ------------------------------------------------------------
# Check D: Numeric validity
# ------------------------------------------------------------

neg_passengers = (
    dataset_df[
        "affected_passengers"
    ] < 0
).sum()

neg_delays = (
    dataset_df[
        "delay_minutes"
    ] < 0
).sum()

neg_durations = (
    dataset_df[
        "disruption_duration_minutes"
    ] < 0
).sum()

neg_impacts = (
    dataset_df[
        "passenger_delay_minutes"
    ] < 0
).sum()

zero_demand = (
    dataset_df[
        "station_daily_passengers"
    ] <= 0
).sum()

invalid_service_share = (
    (
        dataset_df[
            "train_service_share"
        ] < 0.05
    )
    |
    (
        dataset_df[
            "train_service_share"
        ] > 0.50
    )
).sum()

invalid_load_factor = 0

for _, row in dataset_df.iterrows():

    train_type = row[
        "train_type"
    ]

    load_factor = row[
        "train_load_factor"
    ]

    min_lf, max_lf = (
        LOAD_FACTOR_RANGES.get(
            train_type,
            (0.75, 1.15)
        )
    )

    if (
        load_factor < min_lf
        or
        load_factor > max_lf
    ):

        invalid_load_factor += 1


pass_numeric_validity = (
    neg_passengers == 0
    and neg_delays == 0
    and neg_durations == 0
    and neg_impacts == 0
    and zero_demand == 0
    and invalid_service_share == 0
    and invalid_load_factor == 0
)


# ------------------------------------------------------------
# Check E: Bounds
# ------------------------------------------------------------

pass_bounds = (
    dataset_df[
        "delay_minutes"
    ].min() >= 1.0

    and

    dataset_df[
        "delay_minutes"
    ].max() <= 120.0

    and

    dataset_df[
        "disruption_duration_minutes"
    ].min() >= 10.0

    and

    dataset_df[
        "disruption_duration_minutes"
    ].max() <= 180.0

    and

    dataset_df[
        "affected_passengers"
    ].min() >= 1

    and

    dataset_df[
        "passenger_delay_minutes"
    ].min() >= 0.1
)


# ------------------------------------------------------------
# Check F: Time profile
# ------------------------------------------------------------

actual_hourly_weight_sum = (
    hour_probabilities.sum()
)

pass_time_weight_validation = math.isclose(
    actual_hourly_weight_sum,
    1.0,
    rel_tol=0.0,
    abs_tol=1e-12
)


# ------------------------------------------------------------
# Check G: Category coverage
# ------------------------------------------------------------

covered_stations = (
    dataset_df[
        "station_code"
    ].nunique()
)

covered_disruptions = (
    dataset_df[
        "disruption_type"
    ].nunique()
)

covered_train_types = (
    dataset_df[
        "train_type"
    ].nunique()
)

covered_time_periods = (
    dataset_df[
        "time_period"
    ].nunique()
)

covered_days = (
    dataset_df[
        "day_of_week"
    ].nunique()
)

pass_station_coverage = (
    covered_stations == 32
)

pass_disruption_coverage = (
    covered_disruptions == 5
)

pass_train_type_coverage = (
    covered_train_types
    == len(LOAD_FACTOR_RANGES)
)

pass_time_period_coverage = (
    covered_time_periods == 7
)

pass_day_coverage = (
    covered_days == 7
)


# ------------------------------------------------------------
# Check H: Target statistics
# ------------------------------------------------------------

target_series = (
    dataset_df[
        "passenger_delay_minutes"
    ]
)

target_stats = {
    "min": float(
        target_series.min()
    ),
    "max": float(
        target_series.max()
    ),
    "mean": float(
        target_series.mean()
    ),
    "median": float(
        target_series.median()
    ),
    "std": float(
        target_series.std()
    ),
    "p25": float(
        target_series.quantile(
            0.25
        )
    ),
    "p50": float(
        target_series.quantile(
            0.50
        )
    ),
    "p75": float(
        target_series.quantile(
            0.75
        )
    ),
    "p90": float(
        target_series.quantile(
            0.90
        )
    ),
    "p95": float(
        target_series.quantile(
            0.95
        )
    ),
    "p99": float(
        target_series.quantile(
            0.99
        )
    ),
}


# ------------------------------------------------------------
# Check I: Relationships
# ------------------------------------------------------------

corr_demand_affected = float(
    dataset_df[
        "station_daily_passengers"
    ].corr(
        dataset_df[
            "affected_passengers"
        ]
    )
)

corr_delay_impact = float(
    dataset_df[
        "delay_minutes"
    ].corr(
        dataset_df[
            "passenger_delay_minutes"
        ]
    )
)

corr_affected_impact = float(
    dataset_df[
        "affected_passengers"
    ].corr(
        dataset_df[
            "passenger_delay_minutes"
        ]
    )
)

corr_trains_impact = float(
    dataset_df[
        "affected_train_count"
    ].corr(
        dataset_df[
            "passenger_delay_minutes"
        ]
    )
)

peak_impact_mean = float(
    dataset_df[
        dataset_df[
            "is_peak_period"
        ] == 1
    ][
        "passenger_delay_minutes"
    ].mean()
)

nonpeak_impact_mean = float(
    dataset_df[
        dataset_df[
            "is_peak_period"
        ] == 0
    ][
        "passenger_delay_minutes"
    ].mean()
)

pass_relationship_validation = (
    corr_demand_affected > 0.30
    and
    corr_delay_impact > 0.25
    and
    corr_affected_impact > 0.40
    and
    peak_impact_mean > nonpeak_impact_mean
)


# ------------------------------------------------------------
# Check J: Noise bounds
# ------------------------------------------------------------

noise_min = float(
    dataset_df[
        "controlled_noise"
    ].min()
)

noise_max = float(
    dataset_df[
        "controlled_noise"
    ].max()
)

pass_noise_validation = (
    noise_min >= -0.10
    and
    noise_max <= 0.10
)


# ------------------------------------------------------------
# Check K: Disruption coverage
# ------------------------------------------------------------

disruption_type_counts = (
    dataset_df[
        "disruption_type"
    ]
    .value_counts()
    .to_dict()
)


# ------------------------------------------------------------
# Check L: Timetable grounding
# ------------------------------------------------------------

db_train_numbers = set(
    trains_df[
        "train_number"
    ].astype(str)
)

generated_train_numbers = set(
    dataset_df[
        "train_number"
    ].astype(str)
)

unknown_generated_trains = (
    generated_train_numbers
    - db_train_numbers
)

pass_train_grounding = (
    len(
        unknown_generated_trains
    ) == 0
)


# ------------------------------------------------------------
# Check M: Target leakage
# ------------------------------------------------------------

feature_cols = [
    "station_code",
    "station_category",
    "station_daily_passengers",
    "day_of_week",
    "day_type",
    "hour",
    "minute",
    "time_period",
    "is_peak_period",
    "train_type",
    "train_priority",
    "disruption_type",
    "disruption_duration_minutes",
    "delay_minutes",
    "affected_train_count",
]

primary_target = (
    "passenger_delay_minutes"
)

secondary_target = (
    "affected_passengers"
)

forbidden_leakage_columns = [
    primary_target,
    secondary_target,
    "train_passenger_exposure",
    "train_service_share",
    "train_load_factor",
    "disruption_exposure_factor",
    "controlled_noise",
]

target_leakage_columns = [
    col
    for col in forbidden_leakage_columns
    if col in feature_cols
]

pass_target_leakage = (
    len(
        target_leakage_columns
    ) == 0
)


# ============================================================
# 21. BASELINE ML SANITY CHECK
# ============================================================

print(
    "\nRunning Baseline ML Sanity Check "
    "(Random Forest Regressor)..."
)

categorical_cols = [
    "station_code",
    "station_category",
    "day_of_week",
    "day_type",
    "time_period",
    "train_type",
    "disruption_type",
]

encoder = OrdinalEncoder(
    handle_unknown="use_encoded_value",
    unknown_value=-1
)

X_train = train_df[
    feature_cols
].copy()

X_val = val_df[
    feature_cols
].copy()

X_test = test_df[
    feature_cols
].copy()

X_train[
    categorical_cols
] = encoder.fit_transform(
    X_train[
        categorical_cols
    ]
)

X_val[
    categorical_cols
] = encoder.transform(
    X_val[
        categorical_cols
    ]
)

X_test[
    categorical_cols
] = encoder.transform(
    X_test[
        categorical_cols
    ]
)

y_train = train_df[
    primary_target
]

y_val = val_df[
    primary_target
]

y_test = test_df[
    primary_target
]

model = RandomForestRegressor(
    n_estimators=100,
    random_state=SEED,
    n_jobs=-1
)

model.fit(
    X_train,
    y_train
)

val_preds = model.predict(
    X_val
)

test_preds = model.predict(
    X_test
)

val_mae = float(
    mean_absolute_error(
        y_val,
        val_preds
    )
)

val_rmse = float(
    np.sqrt(
        mean_squared_error(
            y_val,
            val_preds
        )
    )
)

val_r2 = float(
    r2_score(
        y_val,
        val_preds
    )
)

test_mae = float(
    mean_absolute_error(
        y_test,
        test_preds
    )
)

test_rmse = float(
    np.sqrt(
        mean_squared_error(
            y_test,
            test_preds
        )
    )
)

test_r2 = float(
    r2_score(
        y_test,
        test_preds
    )
)

print(
    f"Validation Metrics -> "
    f"MAE: {val_mae:,.2f}, "
    f"RMSE: {val_rmse:,.2f}, "
    f"R²: {val_r2:.4f}"
)

print(
    f"Test Metrics       -> "
    f"MAE: {test_mae:,.2f}, "
    f"RMSE: {test_rmse:,.2f}, "
    f"R²: {test_r2:.4f}"
)

pass_baseline_ml = (
    test_r2 >= 0.85
)


# ============================================================
# 22. FEATURE IMPORTANCE
# ============================================================

feature_importance_df = pd.DataFrame(
    {
        "feature": feature_cols,
        "importance": model.feature_importances_,
    }
).sort_values(
    "importance",
    ascending=False
)

feature_importance_path = (
    OUTPUT_DIR
    / "baseline_feature_importance.csv"
)

feature_importance_df.to_csv(
    feature_importance_path,
    index=False
)


# ============================================================
# 23. VISUAL VALIDATION PLOTS
# ============================================================

print(
    "\nGenerating visual validation plots..."
)


# ------------------------------------------------------------
# Plot 1: Passenger impact distribution
# ------------------------------------------------------------

fig, ax = plt.subplots(
    figsize=(8, 5)
)

ax.hist(
    dataset_df[
        "passenger_delay_minutes"
    ],
    bins=50,
    color="#1f77b4",
    edgecolor="black",
    alpha=0.7
)

ax.set_title(
    "Synthetic Passenger Impact Distribution "
    "(Passenger-Delay-Minutes)",
    fontsize=12,
    fontweight="bold"
)

ax.set_xlabel(
    "Passenger Delay Minutes"
)

ax.set_ylabel(
    "Scenario Count"
)

ax.set_yscale(
    "log"
)

ax.grid(
    True,
    linestyle="--",
    alpha=0.5
)

plt.tight_layout()

p1_path = (
    PLOT_DIR
    / "passenger_impact_distribution.png"
)

plt.savefig(
    p1_path,
    dpi=300
)

plt.close()


# ------------------------------------------------------------
# Plot 2: Delay vs passenger impact
# ------------------------------------------------------------

fig, ax = plt.subplots(
    figsize=(8, 5)
)

sc = ax.scatter(
    dataset_df[
        "delay_minutes"
    ],
    dataset_df[
        "passenger_delay_minutes"
    ],
    c=dataset_df[
        "affected_passengers"
    ],
    cmap="viridis",
    alpha=0.4,
    s=15
)

cbar = plt.colorbar(
    sc,
    ax=ax
)

cbar.set_label(
    "Affected Passengers"
)

ax.set_title(
    "Delay Minutes vs Passenger Delay Minutes",
    fontsize=12,
    fontweight="bold"
)

ax.set_xlabel(
    "Delay Minutes"
)

ax.set_ylabel(
    "Passenger Delay Minutes"
)

ax.grid(
    True,
    linestyle="--",
    alpha=0.5
)

plt.tight_layout()

p2_path = (
    PLOT_DIR
    / "delay_vs_passenger_impact.png"
)

plt.savefig(
    p2_path,
    dpi=300
)

plt.close()


# ------------------------------------------------------------
# Plot 3: Station demand vs affected passengers
# ------------------------------------------------------------

fig, ax = plt.subplots(
    figsize=(8, 5)
)

station_avg = (
    dataset_df
    .groupby(
        "station_code"
    )
    .agg(
        {
            "station_daily_passengers": "first",
            "affected_passengers": "mean",
        }
    )
    .reset_index()
)

ax.scatter(
    station_avg[
        "station_daily_passengers"
    ],
    station_avg[
        "affected_passengers"
    ],
    color="#d62728",
    s=60,
    edgecolors="black",
    alpha=0.8
)

for _, r in station_avg.iterrows():

    ax.annotate(
        r["station_code"],
        (
            r[
                "station_daily_passengers"
            ],
            r[
                "affected_passengers"
            ],
        ),
        fontsize=8,
        xytext=(4, 2),
        textcoords="offset points"
    )

ax.set_title(
    "Station Baseline Daily Demand vs "
    "Average Affected Passengers",
    fontsize=12,
    fontweight="bold"
)

ax.set_xlabel(
    "Station Daily Passengers"
)

ax.set_ylabel(
    "Mean Affected Passengers per Disruption"
)

ax.grid(
    True,
    linestyle="--",
    alpha=0.5
)

plt.tight_layout()

p3_path = (
    PLOT_DIR
    / "demand_vs_affected_passengers.png"
)

plt.savefig(
    p3_path,
    dpi=300
)

plt.close()


# ------------------------------------------------------------
# Plot 4: Peak vs non-peak
# ------------------------------------------------------------

fig, ax = plt.subplots(
    figsize=(7, 5)
)

peak_data = [
    dataset_df[
        dataset_df[
            "is_peak_period"
        ] == 0
    ][
        "passenger_delay_minutes"
    ],

    dataset_df[
        dataset_df[
            "is_peak_period"
        ] == 1
    ][
        "passenger_delay_minutes"
    ],
]

ax.boxplot(
    peak_data,
    tick_labels=[
        "Non-Peak Period",
        "Peak Period",
    ],
    patch_artist=True,
    boxprops=dict(
        facecolor="#2ca02c",
        alpha=0.6
    ),
    medianprops=dict(
        color="black"
    )
)

ax.set_title(
    "Passenger Impact: Peak vs Non-Peak Periods",
    fontsize=12,
    fontweight="bold"
)

ax.set_ylabel(
    "Passenger Delay Minutes"
)

ax.set_yscale(
    "log"
)

ax.grid(
    True,
    linestyle="--",
    alpha=0.5
)

plt.tight_layout()

p4_path = (
    PLOT_DIR
    / "peak_vs_nonpeak.png"
)

plt.savefig(
    p4_path,
    dpi=300
)

plt.close()


# ------------------------------------------------------------
# Plot 5: Impact by disruption type
# ------------------------------------------------------------

fig, ax = plt.subplots(
    figsize=(9, 5)
)

disruption_avg = (
    dataset_df
    .groupby(
        "disruption_type"
    )[
        "passenger_delay_minutes"
    ]
    .mean()
    .sort_values(
        ascending=False
    )
)

bars = ax.bar(
    disruption_avg.index,
    disruption_avg.values,
    color="#9467bd",
    edgecolor="black",
    alpha=0.85
)

ax.set_title(
    "Mean Passenger Impact by Disruption Type",
    fontsize=12,
    fontweight="bold"
)

ax.set_xlabel(
    "Disruption Type"
)

ax.set_ylabel(
    "Mean Passenger Delay Minutes"
)

plt.xticks(
    rotation=15,
    ha="right"
)

for bar in bars:

    yval = bar.get_height()

    ax.text(
        bar.get_x()
        + bar.get_width() / 2.0,
        yval + 500,
        f"{yval:,.0f}",
        ha="center",
        va="bottom",
        fontsize=9
    )

ax.grid(
    True,
    linestyle="--",
    alpha=0.5,
    axis="y"
)

plt.tight_layout()

p5_path = (
    PLOT_DIR
    / "impact_by_disruption_type.png"
)

plt.savefig(
    p5_path,
    dpi=300
)

plt.close()


print(
    f"Generated 5 visual validation plots in: "
    f"{PLOT_DIR}"
)


# ============================================================
# 24. GENERATION METADATA JSON
# ============================================================

metadata = {
    "generation_timestamp":
        pd.Timestamp.now().isoformat(),

    "random_seed":
        SEED,

    "number_of_scenarios":
        TOTAL_SCENARIOS,

    "formula_version":
        "v1.2-interpretable-synthetic",

    "formula_description":
        "BaseTypeFactor is applied only through "
        "DisruptionExposureFactor. SeverityFactor "
        "contains only PeakMultiplier and "
        "PriorityMultiplier to avoid double-counting "
        "disruption type.",

    "time_profile_version":
        "v1.1-7-period-normalized",

    "raw_time_weight_sum":
        raw_weight_total,

    "normalized_time_weight_sum":
        normalized_weight_total,

    "time_period_weights": {
        tp["name"]:
            tp["period_weight"]
        for tp in TIME_PERIODS
    },

    "noise_range": [
        -0.10,
        0.10
    ],

    "train_exposure_methodology":
        "TimeDependentStationDemand "
        "x TimetableGroundedTrainServiceShare "
        "x TrainLoadFactor",

    "train_selection_methodology":
        "Train selected from timetable services "
        "operationally relevant to generated "
        "station/time/day scenario",

    "train_service_share_methodology":
        "Capacity-weighted share among "
        "time-relevant timetable services",

    "disruption_factor_methodology":
        "DisruptionBaseFactor "
        "x TrainCountMultiplier "
        "x DurationMultiplier",

    "severity_factor_methodology":
        "PeakMultiplier "
        "x PriorityMultiplier",

    "target_formula":
        "AffectedPassengers "
        "= TrainPassengerExposure "
        "x DisruptionExposureFactor; "
        "PassengerDelayMinutes "
        "= AffectedPassengers "
        "x DelayMinutes "
        "x SeverityFactor "
        "x (1 + ControlledNoise)",

    "load_factor_ranges":
        LOAD_FACTOR_RANGES,

    "train_capacity_ratios":
        TRAIN_CAPACITY_RATIO,

    "disruption_base_factors":
        DISRUPTION_BASE_FACTOR,

    "delay_distribution":
        {
            f"{b['range'][0]}-{b['range'][1]}":
                b["prob"]
            for b in DELAY_BINS
        },

    "feature_list":
        feature_cols,

    "primary_target":
        primary_target,

    "secondary_target":
        secondary_target,

    "target_leakage_columns":
        target_leakage_columns,

    "train_validation_test_split": {
        "train_ratio":
            TRAIN_RATIO,

        "val_ratio":
            VAL_RATIO,

        "test_ratio":
            TEST_RATIO,

        "train_count":
            len(train_df),

        "val_count":
            len(val_df),

        "test_count":
            len(test_df),
    },

    "validation_summary": {
        "total_missing":
            int(
                total_missing
            ),

        "duplicate_scenarios":
            int(
                duplicate_scenarios
            ),

        "time_weight_sum":
            float(
                actual_hourly_weight_sum
            ),

        "noise_min":
            noise_min,

        "noise_max":
            noise_max,

        "train_grounding_pass":
            bool(
                pass_train_grounding
            ),

        "target_leakage_pass":
            bool(
                pass_target_leakage
            ),

        "relationship_validation_pass":
            bool(
                pass_relationship_validation
            ),

        "baseline_ml_test_r2":
            test_r2,
    },
}


metadata_path = (
    OUTPUT_DIR
    / "generation_metadata.json"
)

with open(
    metadata_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        metadata,
        f,
        indent=4
    )

print(
    f"Saved metadata to: "
    f"{metadata_path}"
)


# ============================================================
# 25. DATA QUALITY REPORT
# ============================================================

overall_validation_pass = all(
    [
        pass_row_counts,
        pass_missing,
        pass_duplicates,
        pass_numeric_validity,
        pass_bounds,
        pass_time_weight_validation,
        pass_station_coverage,
        pass_disruption_coverage,
        pass_train_type_coverage,
        pass_time_period_coverage,
        pass_day_coverage,
        pass_relationship_validation,
        pass_noise_validation,
        pass_train_grounding,
        pass_target_leakage,
        pass_baseline_ml,
    ]
)


report_text = f"""
================================================================================
PASSENGER IMPACT SYNTHETIC DATASET VALIDATION REPORT
================================================================================

1. DATASET GENERATION SUMMARY
-----------------------------
This dataset is synthetic and is intended for Phase 1 passenger-impact ML
prototyping.

It is NOT historical railway passenger-disruption data.

- Total Generated Scenarios : {TOTAL_SCENARIOS:,}
- Random Seed               : {SEED}

2. FORMULA USED
---------------

Formula Version:
v1.2-interpretable-synthetic

AffectedPassengers =
    TrainPassengerExposure
    * DisruptionExposureFactor

PassengerDelayMinutes =
    AffectedPassengers
    * DelayMinutes
    * SeverityFactor
    * (1 + ControlledNoise)

Where:

TrainPassengerExposure =
    StationDailyPassengers
    * TimeOfDayWeight
    * TrainServiceShare
    * TrainLoadFactor

TrainServiceShare =
    CapacityWeightedSelectedTrainShare
    among time-relevant timetable services.

DisruptionExposureFactor =
    BaseTypeFactor
    * TrainCountFactor
    * DurationFactor

SeverityFactor =
    PeakMultiplier
    * PriorityMultiplier

IMPORTANT FORMULA DESIGN:
BaseTypeFactor is applied only through
DisruptionExposureFactor.

BaseTypeFactor is NOT applied again through
SeverityFactor.

This prevents double-counting the disruption type.

ControlledNoise =
    Uniform(-0.10, +0.10)

3. TIME-OF-DAY WEIGHTING
------------------------

Raw weight sum:
- {raw_weight_total:.6f}

Normalized weight sum:
- {normalized_weight_total:.12f}

Actual hourly probability sum:
- {actual_hourly_weight_sum:.12f}

Normalized period weights:

"""

for tp in TIME_PERIODS:

    report_text += (
        f"- {tp['start_hour']:02d}:00-"
        f"{tp['end_hour']:02d}:59 "
        f"{tp['name']:<20} : "
        f"{tp['period_weight']:.8f} "
        f"({tp['hours']} hrs)"
        "\n"
    )


report_text += f"""
Status:
- {"PASS" if pass_time_weight_validation else "FAIL"}

4. TRAIN EXPOSURE METHODOLOGY
-----------------------------

- Station baseline demand is derived from:
  project_station_passenger_data.csv

- Station count:
  {len(station_codes)}

- Train selection is grounded in the validated SQLite timetable.

- Selected trains are operationally relevant to the generated
  station/time/day scenario.

- Train service share uses capacity-weighted timetable services
  around the generated scenario time.

- Train load factors are bounded by train type.

5. TRAIN LOAD FACTOR RANGES
----------------------------

"""

for train_type, (
    minimum,
    maximum
) in LOAD_FACTOR_RANGES.items():

    report_text += (
        f"- {train_type:<15}: "
        f"{minimum:.2f}-{maximum:.2f}\n"
    )


report_text += f"""
6. DISRUPTION TYPES
-------------------

"""

for disruption_type in DISRUPTION_TYPES:

    report_text += (
        f"- {disruption_type:<30}: "
        f"{DISRUPTION_BASE_FACTOR[disruption_type]:.2f}\n"
    )


report_text += f"""
7. DISRUPTION DURATION
----------------------

- Minimum : 10 minutes
- Maximum : 180 minutes

8. AFFECTED TRAIN COUNT
-----------------------

- Minimum : 1
- Maximum : 18

9. DELAY DISTRIBUTION
---------------------

"""

for delay_bin in DELAY_BINS:

    report_text += (
        f"- "
        f"{delay_bin['range'][0]:.0f}-"
        f"{delay_bin['range'][1]:.0f} mins"
        f" : {delay_bin['prob'] * 100:.1f}%\n"
    )


report_text += f"""
10. NOISE METHODOLOGY
---------------------

- Minimum observed noise : {noise_min:.5f}
- Maximum observed noise : {noise_max:.5f}
- Allowed range          : -0.10 to +0.10

Status:
- {"PASS" if pass_noise_validation else "FAIL"}

11. DATASET COUNTS
------------------

- Total      : {total_rows:,}
- Training   : {train_rows:,}
- Validation : {val_rows:,}
- Test       : {test_rows:,}

12. MISSING VALUES
------------------

- Total Missing Values : {total_missing}
- Status               : {"PASS" if pass_missing else "FAIL"}

13. DUPLICATE CHECK
-------------------

- Duplicate Scenario IDs : {duplicate_scenarios}
- Status                 : {"PASS" if pass_duplicates else "FAIL"}

14. NUMERIC VALIDITY
--------------------

- Negative Passengers       : {neg_passengers}
- Negative Delays           : {neg_delays}
- Negative Durations        : {neg_durations}
- Negative Impact Values    : {neg_impacts}
- Zero/Negative Demand      : {zero_demand}
- Invalid Service Shares    : {invalid_service_share}
- Invalid Load Factors      : {invalid_load_factor}

Status:
- {"PASS" if pass_numeric_validity else "FAIL"}

15. RANGE VALIDATION
--------------------

- Delay range:
  {dataset_df["delay_minutes"].min():.2f}
  to
  {dataset_df["delay_minutes"].max():.2f}

- Disruption duration range:
  {dataset_df["disruption_duration_minutes"].min():.2f}
  to
  {dataset_df["disruption_duration_minutes"].max():.2f}

- Minimum affected passengers:
  {dataset_df["affected_passengers"].min()}

- Minimum passenger impact:
  {dataset_df["passenger_delay_minutes"].min():.2f}

Status:
- {"PASS" if pass_bounds else "FAIL"}

16. CATEGORY COVERAGE
---------------------

- Station Coverage:
  {covered_stations}/32

- Disruption Coverage:
  {covered_disruptions}/5

- Train Type Coverage:
  {covered_train_types}/11

- Time Period Coverage:
  {covered_time_periods}/7

- Day Coverage:
  {covered_days}/7

Status:
- Stations    : {"PASS" if pass_station_coverage else "FAIL"}
- Disruptions : {"PASS" if pass_disruption_coverage else "FAIL"}
- Train Types : {"PASS" if pass_train_type_coverage else "FAIL"}
- Time Period : {"PASS" if pass_time_period_coverage else "FAIL"}
- Days        : {"PASS" if pass_day_coverage else "FAIL"}

17. TARGET STATISTICS
---------------------

Target:
passenger_delay_minutes

- Minimum : {target_stats["min"]:,.2f}
- Maximum : {target_stats["max"]:,.2f}
- Mean    : {target_stats["mean"]:,.2f}
- Median  : {target_stats["median"]:,.2f}
- Std Dev : {target_stats["std"]:,.2f}
- P25     : {target_stats["p25"]:,.2f}
- P50     : {target_stats["p50"]:,.2f}
- P75     : {target_stats["p75"]:,.2f}
- P90     : {target_stats["p90"]:,.2f}
- P95     : {target_stats["p95"]:,.2f}
- P99     : {target_stats["p99"]:,.2f}

18. SYNTHETIC RELATIONSHIPS
---------------------------

- Station Demand vs Affected Passengers :
  {corr_demand_affected:.4f}

- Delay Minutes vs Passenger Impact :
  {corr_delay_impact:.4f}

- Affected Passengers vs Impact :
  {corr_affected_impact:.4f}

- Affected Train Count vs Impact :
  {corr_trains_impact:.4f}

- Peak Period Mean Impact :
  {peak_impact_mean:,.2f}

- Non-Peak Period Mean Impact :
  {nonpeak_impact_mean:,.2f}

Status:
- {"PASS" if pass_relationship_validation else "FAIL"}

19. TIMETABLE GROUNDING
-----------------------

- Generated train numbers found in DB :
  {len(generated_train_numbers)}

- Unknown generated train numbers :
  {len(unknown_generated_trains)}

Status:
- {"PASS" if pass_train_grounding else "FAIL"}

20. TARGET LEAKAGE CHECK
------------------------

ML feature columns:

"""

for feature in feature_cols:

    report_text += (
        f"- {feature}\n"
    )


report_text += f"""
Excluded from ML features because they are derived target-side
quantities or intermediate calculations:

- passenger_delay_minutes
- affected_passengers
- train_passenger_exposure
- train_service_share
- train_load_factor
- disruption_exposure_factor
- controlled_noise

Target leakage columns detected:
{target_leakage_columns}

Status:
- {"PASS" if pass_target_leakage else "FAIL"}

21. BASELINE ML SANITY CHECK
----------------------------

Model:
RandomForestRegressor

Parameters:
- n_estimators = 100
- random_state = 42

Validation:
- MAE  : {val_mae:,.2f}
- RMSE : {val_rmse:,.2f}
- R²   : {val_r2:.4f}

Test:
- MAE  : {test_mae:,.2f}
- RMSE : {test_rmse:,.2f}
- R²   : {test_r2:.4f}

Sanity threshold:
- Test R² >= 0.85

Status:
- {"PASS" if pass_baseline_ml else "FAIL"}

22. IMPORTANT LIMITATIONS
-------------------------

- This dataset is synthetic.
- It is not historical disruption data.
- Station demand is based on station-level baseline passenger data.
- Passenger impact labels are generated using an interpretable synthetic
  scenario model.
- Train service selection is grounded in the validated project timetable.
- Train service share is an estimate based on timetable service density
  and relative train capacity.
- Train load factors are controlled synthetic ranges.
- BaseTypeFactor is applied once through DisruptionExposureFactor.
- SeverityFactor contains peak-period and train-priority effects only.
- Synthetic data should be treated as Phase 1 ML prototyping data.
- Real-world validation will be required when historical disruption and
  passenger-impact observations become available.

23. OVERALL VALIDATION STATUS
----------------------------

Overall validation:
{"PASS" if overall_validation_pass else "FAIL"}

================================================================================
"""


report_path = (
    OUTPUT_DIR
    / "passenger_impact_dataset_validation_report.txt"
)

with open(
    report_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        report_text
    )

print(
    f"Saved validation report to: "
    f"{report_path}"
)


# ============================================================
# 26. FINAL TERMINAL SUMMARY
# ============================================================

print()

print("=" * 70)

print(
    "PASSENGER IMPACT DATASET GENERATION COMPLETE"
)

print("=" * 70)

print()

print(
    f"Formula version         : "
    f"v1.2-interpretable-synthetic"
)

print(
    "Double-counting fix     : "
    "BaseTypeFactor applied once"
)

print()

print(
    f"Source project stations : "
    f"{len(station_codes)}"
)

print(
    f"Synthetic scenarios     : "
    f"{total_rows:,}"
)

print(
    f"Training                : "
    f"{train_rows:,}"
)

print(
    f"Validation              : "
    f"{val_rows:,}"
)

print(
    f"Test                    : "
    f"{test_rows:,}"
)

print()

print(
    "Primary target          : "
    "passenger_delay_minutes"
)

print(
    "Secondary target        : "
    "affected_passengers"
)

print()

print(
    "Time-weight validation  : "
    + (
        "PASS"
        if pass_time_weight_validation
        else "FAIL"
    )
)

print(
    "Missing values          : "
    + (
        "PASS"
        if pass_missing
        else "FAIL"
    )
)

print(
    "Duplicate scenarios     : "
    + (
        "PASS"
        if pass_duplicates
        else "FAIL"
    )
)

print(
    "Numeric validation      : "
    + (
        "PASS"
        if pass_numeric_validity
        else "FAIL"
    )
)

print(
    "Range validation        : "
    + (
        "PASS"
        if pass_bounds
        else "FAIL"
    )
)

print(
    "Station coverage        : "
    + (
        "PASS"
        if pass_station_coverage
        else "FAIL"
    )
)

print(
    "Disruption coverage     : "
    + (
        "PASS"
        if pass_disruption_coverage
        else "FAIL"
    )
)

print(
    "Train-type coverage     : "
    + (
        "PASS"
        if pass_train_type_coverage
        else "FAIL"
    )
)

print(
    "Time-period coverage    : "
    + (
        "PASS"
        if pass_time_period_coverage
        else "FAIL"
    )
)

print(
    "Day coverage            : "
    + (
        "PASS"
        if pass_day_coverage
        else "FAIL"
    )
)

print(
    "Noise validation        : "
    + (
        "PASS"
        if pass_noise_validation
        else "FAIL"
    )
)

print(
    "Train grounding         : "
    + (
        "PASS"
        if pass_train_grounding
        else "FAIL"
    )
)

print(
    "Target leakage check    : "
    + (
        "PASS"
        if pass_target_leakage
        else "FAIL"
    )
)

print(
    "Relationship validation: "
    + (
        "PASS"
        if pass_relationship_validation
        else "FAIL"
    )
)

print(
    "Baseline ML sanity      : "
    + (
        "PASS"
        if pass_baseline_ml
        else "FAIL"
    )
)

print()

print(
    "Overall validation      : "
    + (
        "PASS"
        if overall_validation_pass
        else "FAIL"
    )
)

print()

print(
    "Output directory:"
)

print(
    "data/processed/passenger_ml/"
)

print("=" * 70)