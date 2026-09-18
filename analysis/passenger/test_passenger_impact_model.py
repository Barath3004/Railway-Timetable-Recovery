"""
Passenger Impact ML Model - Behavioral Validation
==================================================

Purpose:
    Validate whether the trained Passenger Impact ML model responds
    logically when important scenario variables are changed.

Tests:
    1. Delay increase
    2. Disruption duration increase
    3. Affected train count increase
    4. Off-peak -> Peak
    5. Low-demand -> High-demand station
    6. Disruption type comparison

This is a behavioral/sensitivity test.
It does NOT retrain the model.

Expected behavior:
    Increasing passenger exposure or delay should generally increase
    predicted passenger_delay_minutes.
"""

from pathlib import Path

import joblib
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "passenger_ml"
    / "final_model"
    / "passenger_impact_model.joblib"
)


# ============================================================
# MODEL FEATURES
# ============================================================

FEATURE_COLUMNS = [
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


# ============================================================
# BASE SCENARIO
# ============================================================

BASE_SCENARIO = {
    "station_code": "MDU",
    "station_category": "NSG2",
    "station_daily_passengers": 18360,
    "day_of_week": "Friday",
    "day_type": "Weekday",
    "hour": 18,
    "minute": 15,
    "time_period": "Evening peak",
    "is_peak_period": 1,
    "train_type": "Express",
    "train_priority": 1,
    "disruption_type": "TRACK_FAILURE",
    "disruption_duration_minutes": 60,
    "delay_minutes": 20,
    "affected_train_count": 2,
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def predict(model, scenario):
    """Predict passenger delay minutes for one scenario."""

    df = pd.DataFrame([scenario])

    features = df[FEATURE_COLUMNS]

    prediction = model.predict(features)[0]

    return max(0.0, float(prediction))


def percentage_change(base, changed):
    """Calculate percentage change from base to changed."""

    if base == 0:
        return 0.0

    return ((changed - base) / base) * 100.0


def print_test_result(
    test_name,
    base_value,
    changed_value,
    expected_direction,
    variable_name,
):
    """Print one behavioral test result."""

    change = percentage_change(
        base_value,
        changed_value,
    )

    if expected_direction == "increase":
        passed = changed_value > base_value
    elif expected_direction == "decrease":
        passed = changed_value < base_value
    else:
        passed = True

    status = "PASS" if passed else "FAIL"

    print()
    print(f"{test_name}")
    print("-" * 70)
    print(f"Changed variable : {variable_name}")
    print(f"Base prediction  : {base_value:,.2f}")
    print(f"New prediction   : {changed_value:,.2f}")
    print(f"Change           : {change:+.2f}%")
    print(f"Expected         : {expected_direction.upper()}")
    print(f"Result           : {status}")

    return passed


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("PASSENGER IMPACT ML MODEL - BEHAVIORAL VALIDATION")
    print("=" * 70)

    print()
    print(f"Model path: {MODEL_PATH}")

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Trained model not found:\n{MODEL_PATH}"
        )

    # --------------------------------------------------------
    # Load model
    # --------------------------------------------------------

    print()
    print("Loading trained model...")

    model = joblib.load(MODEL_PATH)

    print("Model loaded successfully.")

    results = []

    # ========================================================
    # TEST 1 - DELAY
    # ========================================================

    base = BASE_SCENARIO.copy()

    changed = BASE_SCENARIO.copy()
    changed["delay_minutes"] = 60

    base_prediction = predict(model, base)
    changed_prediction = predict(model, changed)

    passed = print_test_result(
        "TEST 1 - Delay Sensitivity",
        base_prediction,
        changed_prediction,
        "increase",
        "delay_minutes: 20 -> 60",
    )

    results.append(
        {
            "test": "Delay Sensitivity",
            "base_prediction": base_prediction,
            "changed_prediction": changed_prediction,
            "expected": "Increase",
            "passed": passed,
        }
    )

    # ========================================================
    # TEST 2 - DISRUPTION DURATION
    # ========================================================

    base = BASE_SCENARIO.copy()

    changed = BASE_SCENARIO.copy()
    changed["disruption_duration_minutes"] = 120

    base_prediction = predict(model, base)
    changed_prediction = predict(model, changed)

    passed = print_test_result(
        "TEST 2 - Disruption Duration Sensitivity",
        base_prediction,
        changed_prediction,
        "increase",
        "disruption_duration_minutes: 60 -> 120",
    )

    results.append(
        {
            "test": "Disruption Duration Sensitivity",
            "base_prediction": base_prediction,
            "changed_prediction": changed_prediction,
            "expected": "Increase",
            "passed": passed,
        }
    )

    # ========================================================
    # TEST 3 - AFFECTED TRAIN COUNT
    # ========================================================

    base = BASE_SCENARIO.copy()

    changed = BASE_SCENARIO.copy()
    changed["affected_train_count"] = 6

    base_prediction = predict(model, base)
    changed_prediction = predict(model, changed)

    passed = print_test_result(
        "TEST 3 - Affected Train Count Sensitivity",
        base_prediction,
        changed_prediction,
        "increase",
        "affected_train_count: 2 -> 6",
    )

    results.append(
        {
            "test": "Affected Train Count Sensitivity",
            "base_prediction": base_prediction,
            "changed_prediction": changed_prediction,
            "expected": "Increase",
            "passed": passed,
        }
    )

    # ========================================================
    # TEST 4 - OFF-PEAK VS PEAK
    # ========================================================

    base = BASE_SCENARIO.copy()

    base["hour"] = 11
    base["minute"] = 30
    base["time_period"] = "Midday"
    base["is_peak_period"] = 0

    changed = base.copy()
    changed["hour"] = 18
    changed["minute"] = 15
    changed["time_period"] = "Evening peak"
    changed["is_peak_period"] = 1

    base_prediction = predict(model, base)
    changed_prediction = predict(model, changed)

    passed = print_test_result(
        "TEST 4 - Peak vs Off-Peak Sensitivity",
        base_prediction,
        changed_prediction,
        "increase",
        "Midday/off-peak -> Evening peak",
    )

    results.append(
        {
            "test": "Peak vs Off-Peak Sensitivity",
            "base_prediction": base_prediction,
            "changed_prediction": changed_prediction,
            "expected": "Increase",
            "passed": passed,
        }
    )

    # ========================================================
    # TEST 5 - STATION DEMAND
    # ========================================================

    base = BASE_SCENARIO.copy()

    base["station_code"] = "TVP"
    base["station_category"] = "NSG3"
    base["station_daily_passengers"] = 412

    changed = BASE_SCENARIO.copy()

    changed["station_code"] = "MAS"
    changed["station_category"] = "NSG1"
    changed["station_daily_passengers"] = 65000

    base_prediction = predict(model, base)
    changed_prediction = predict(model, changed)

    passed = print_test_result(
        "TEST 5 - Station Passenger Demand Sensitivity",
        base_prediction,
        changed_prediction,
        "increase",
        "Daily passengers: 412 -> 65,000",
    )

    results.append(
        {
            "test": "Station Passenger Demand Sensitivity",
            "base_prediction": base_prediction,
            "changed_prediction": changed_prediction,
            "expected": "Increase",
            "passed": passed,
        }
    )

    # ========================================================
    # TEST 6 - DISRUPTION TYPE
    # ========================================================

    disruption_types = [
        "PLATFORM_CLOSURE",
        "TRACK_FAILURE",
        "SIGNAL_FAILURE",
        "PLANNED_MAINTENANCE",
        "OTHER_RESOURCE_DISRUPTION",
    ]

    print()
    print("=" * 70)
    print("TEST 6 - DISRUPTION TYPE COMPARISON")
    print("=" * 70)

    disruption_results = []

    for disruption_type in disruption_types:

        scenario = BASE_SCENARIO.copy()
        scenario["disruption_type"] = disruption_type

        prediction = predict(
            model,
            scenario,
        )

        disruption_results.append(
            {
                "disruption_type": disruption_type,
                "prediction": prediction,
            }
        )

        print(
            f"{disruption_type:<30} "
            f"{prediction:>15,.2f}"
        )

    # --------------------------------------------------------
    # Check disruption ordering
    # --------------------------------------------------------

    disruption_df = pd.DataFrame(
        disruption_results
    )

    sorted_disruptions = (
        disruption_df
        .sort_values(
            "prediction",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    print()
    print("Ranking by predicted passenger impact:")
    print()

    for index, row in sorted_disruptions.iterrows():

        print(
            f"{index + 1}. "
            f"{row['disruption_type']:<30} "
            f"{row['prediction']:>15,.2f}"
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print("BEHAVIORAL VALIDATION SUMMARY")
    print("=" * 70)

    passed_count = sum(
        1
        for result in results
        if result["passed"]
    )

    total_tests = len(results)

    print()
    print(
        f"Directional tests passed : "
        f"{passed_count}/{total_tests}"
    )

    print()
    for result in results:

        status = (
            "PASS"
            if result["passed"]
            else "FAIL"
        )

        print(
            f"{status:<6} "
            f"{result['test']}"
        )

    # --------------------------------------------------------
    # Important interpretation
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("INTERPRETATION")
    print("=" * 70)

    print(
        """
These tests check whether the trained model responds in the
expected direction when important input variables change.

PASS means the prediction moved in the expected direction.

A FAIL does not automatically mean the model is unusable.
Tree-based models can learn nonlinear interactions, so a single
feature change can occasionally produce an unexpected local
response.

The results should therefore be evaluated together with the
training/test metrics and the synthetic-data generation logic.
"""
    )

    print("=" * 70)
    print("BEHAVIORAL VALIDATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()