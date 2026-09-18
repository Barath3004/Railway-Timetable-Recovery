"""
Passenger Impact ML - Multi-Model Training and Evaluation
===========================================================

Purpose:
    Train, evaluate and compare four regression models for predicting
    passenger_delay_minutes for Railway Timetable Recovery Phase 1.

Models:
    1. Random Forest Regressor
    2. Extra Trees Regressor
    3. Gradient Boosting Regressor
    4. HistGradientBoosting Regressor

Final Phase 1 Model:
    HistGradientBoosting Regressor

Evaluation:
    Stage 1:
        - Validation MAE
        - Validation RMSE
        - Validation R2
        - Test MAE
        - Test RMSE
        - Test R2

    Stage 2:
        - Railway behavioral scenario tests
        - Candidate evaluation scenario
        - Directional behavior checks

Important:
    The same train/validation/test datasets and target variable are used
    for all four models.

    The ML model estimates passenger impact. It does NOT optimize or
    select the railway timetable. ALNS remains the optimizer.

    HistGradientBoosting is the finalized Passenger Impact model for
    Phase 1 based on quantitative evaluation and behavioral validation.
"""

import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


warnings.filterwarnings("ignore")


# ============================================================
# CONFIGURATION
# ============================================================

SEED = 42

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "passenger_ml"
)

COMPARISON_MODEL_DIR = (
    DATASET_DIR
    / "comparison_models"
)

EVALUATION_DIR = (
    DATASET_DIR
    / "evaluation"
)

FINAL_MODEL_DIR = (
    DATASET_DIR
    / "final_model"
)

TRAIN_FILE = (
    DATASET_DIR
    / "train.csv"
)

VALIDATION_FILE = (
    DATASET_DIR
    / "validation.csv"
)

TEST_FILE = (
    DATASET_DIR
    / "test.csv"
)

TARGET_COLUMN = "passenger_delay_minutes"


# ============================================================
# FEATURES
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


CATEGORICAL_FEATURES = [
    "station_code",
    "station_category",
    "day_of_week",
    "day_type",
    "time_period",
    "train_type",
    "disruption_type",
]


NUMERIC_FEATURES = [
    "station_daily_passengers",
    "hour",
    "minute",
    "is_peak_period",
    "train_priority",
    "disruption_duration_minutes",
    "delay_minutes",
    "affected_train_count",
]


# ============================================================
# MODEL CONFIGURATION
# ============================================================

MODEL_NAMES = [
    "Random Forest",
    "Extra Trees",
    "Gradient Boosting",
    "HistGradientBoosting",
]


FINAL_MODEL_NAME = "HistGradientBoosting"


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def print_section(title):

    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def calculate_metrics(y_true, y_pred):

    return {
        "MAE": float(
            mean_absolute_error(
                y_true,
                y_pred,
            )
        ),
        "RMSE": float(
            np.sqrt(
                mean_squared_error(
                    y_true,
                    y_pred,
                )
            )
        ),
        "R2": float(
            r2_score(
                y_true,
                y_pred,
            )
        ),
    }


def validate_columns(df, dataset_name):

    required_columns = set(
        FEATURE_COLUMNS + [TARGET_COLUMN]
    )

    missing_columns = (
        required_columns - set(df.columns)
    )

    if missing_columns:

        raise ValueError(
            f"{dataset_name} is missing required columns: "
            f"{sorted(missing_columns)}"
        )


def validate_target(df, dataset_name):

    if df[TARGET_COLUMN].isna().any():

        raise ValueError(
            f"{dataset_name} contains missing target values."
        )

    if (df[TARGET_COLUMN] < 0).any():

        raise ValueError(
            f"{dataset_name} contains negative "
            f"passenger-delay values."
        )


def build_preprocessor(sparse_output=True):

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                ),
            )
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="most_frequent"
                ),
            ),
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=sparse_output,
                ),
            ),
        ]
    )

    return ColumnTransformer(
        transformers=[
            (
                "numeric",
                numeric_pipeline,
                NUMERIC_FEATURES,
            ),
            (
                "categorical",
                categorical_pipeline,
                CATEGORICAL_FEATURES,
            ),
        ]
    )


def build_model_pipelines():

    # --------------------------------------------------------
    # Random Forest
    # --------------------------------------------------------

    random_forest = RandomForestRegressor(
        n_estimators=300,
        random_state=SEED,
        n_jobs=-1,
        max_features="sqrt",
        min_samples_leaf=2,
    )

    rf_pipeline = Pipeline(
        steps=[
            (
                "preprocessor",
                build_preprocessor(
                    sparse_output=True
                ),
            ),
            (
                "model",
                random_forest,
            ),
        ]
    )

    # --------------------------------------------------------
    # Extra Trees
    # --------------------------------------------------------

    extra_trees = ExtraTreesRegressor(
        n_estimators=300,
        random_state=SEED,
        n_jobs=-1,
        max_features="sqrt",
        min_samples_leaf=2,
    )

    et_pipeline = Pipeline(
        steps=[
            (
                "preprocessor",
                build_preprocessor(
                    sparse_output=True
                ),
            ),
            (
                "model",
                extra_trees,
            ),
        ]
    )

    # --------------------------------------------------------
    # Gradient Boosting
    # --------------------------------------------------------

    gradient_boosting = GradientBoostingRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=3,
        min_samples_leaf=2,
        random_state=SEED,
    )

    gb_pipeline = Pipeline(
        steps=[
            (
                "preprocessor",
                build_preprocessor(
                    sparse_output=False
                ),
            ),
            (
                "model",
                gradient_boosting,
            ),
        ]
    )

    # --------------------------------------------------------
    # HistGradientBoosting
    # --------------------------------------------------------

    hist_gradient_boosting = (
        HistGradientBoostingRegressor(
            max_iter=300,
            learning_rate=0.05,
            max_leaf_nodes=31,
            l2_regularization=0.1,
            random_state=SEED,
        )
    )

    hgb_pipeline = Pipeline(
        steps=[
            (
                "preprocessor",
                build_preprocessor(
                    sparse_output=False
                ),
            ),
            (
                "model",
                hist_gradient_boosting,
            ),
        ]
    )

    return {
        "Random Forest": rf_pipeline,
        "Extra Trees": et_pipeline,
        "Gradient Boosting": gb_pipeline,
        "HistGradientBoosting": hgb_pipeline,
    }


def evaluate_model(
    pipeline,
    X_train,
    y_train,
    X_validation,
    y_validation,
    X_test,
    y_test,
):

    pipeline.fit(
        X_train,
        y_train,
    )

    validation_predictions = pipeline.predict(
        X_validation
    )

    test_predictions = pipeline.predict(
        X_test
    )

    validation_metrics = calculate_metrics(
        y_validation,
        validation_predictions,
    )

    test_metrics = calculate_metrics(
        y_test,
        test_predictions,
    )

    return (
        validation_metrics,
        test_metrics,
    )


# ============================================================
# SCENARIO TESTING
# ============================================================

def create_scenario(
    station_code,
    station_category,
    station_daily_passengers,
    day_of_week,
    day_type,
    hour,
    minute,
    time_period,
    is_peak_period,
    train_type,
    train_priority,
    disruption_type,
    disruption_duration_minutes,
    delay_minutes,
    affected_train_count,
):

    return {
        "station_code": station_code,
        "station_category": station_category,
        "station_daily_passengers": station_daily_passengers,
        "day_of_week": day_of_week,
        "day_type": day_type,
        "hour": hour,
        "minute": minute,
        "time_period": time_period,
        "is_peak_period": is_peak_period,
        "train_type": train_type,
        "train_priority": train_priority,
        "disruption_type": disruption_type,
        "disruption_duration_minutes": (
            disruption_duration_minutes
        ),
        "delay_minutes": delay_minutes,
        "affected_train_count": affected_train_count,
    }


def run_behavioral_scenarios(models):

    print_section(
        "STAGE 2 - BEHAVIORAL SCENARIO VALIDATION"
    )

    scenarios = {}

    base = create_scenario(
        station_code="MDU",
        station_category="NSG2",
        station_daily_passengers=18360,
        day_of_week="Friday",
        day_type="Weekday",
        hour=18,
        minute=15,
        time_period="Evening",
        is_peak_period=1,
        train_type="Express",
        train_priority=1,
        disruption_type="TRACK_FAILURE",
        disruption_duration_minutes=60,
        delay_minutes=20,
        affected_train_count=2,
    )

    scenarios["Base"] = base

    delay_high = base.copy()
    delay_high["delay_minutes"] = 60

    scenarios["Delay Increased"] = delay_high

    duration_high = base.copy()

    duration_high[
        "disruption_duration_minutes"
    ] = 120

    scenarios["Duration Increased"] = duration_high

    trains_high = base.copy()

    trains_high[
        "affected_train_count"
    ] = 6

    scenarios["Affected Trains Increased"] = trains_high

    off_peak = base.copy()

    off_peak["hour"] = 13
    off_peak["minute"] = 15
    off_peak["time_period"] = "Afternoon"
    off_peak["is_peak_period"] = 0

    scenarios["Off Peak"] = off_peak

    low_demand = base.copy()

    low_demand[
        "station_code"
    ] = "TVP"

    low_demand[
        "station_category"
    ] = "NSG5"

    low_demand[
        "station_daily_passengers"
    ] = 412

    scenarios["Low Demand Station"] = low_demand

    high_demand = base.copy()

    high_demand[
        "station_code"
    ] = "MAS"

    high_demand[
        "station_category"
    ] = "NSG1"

    high_demand[
        "station_daily_passengers"
    ] = 65000

    scenarios["High Demand Station"] = high_demand

    scenario_rows = []

    for scenario_name, scenario in scenarios.items():

        row = {
            "scenario": scenario_name
        }

        scenario_df = pd.DataFrame(
            [scenario]
        )

        for model_name, pipeline in models.items():

            prediction = pipeline.predict(
                scenario_df
            )[0]

            prediction = max(
                0.0,
                float(prediction),
            )

            row[model_name] = prediction

        scenario_rows.append(row)

    scenario_df = pd.DataFrame(
        scenario_rows
    )

    print()
    print(
        scenario_df.to_string(
            index=False
        )
    )

    return scenario_df


def run_disruption_type_scenarios(models):

    print_section(
        "DISRUPTION TYPE BEHAVIOR TEST"
    )

    disruption_types = [
        "PLATFORM_CLOSURE",
        "TRACK_FAILURE",
        "SIGNAL_FAILURE",
        "PLANNED_MAINTENANCE",
        "OTHER_RESOURCE_DISRUPTION",
    ]

    rows = []

    for disruption_type in disruption_types:

        scenario = create_scenario(
            station_code="MDU",
            station_category="NSG2",
            station_daily_passengers=18360,
            day_of_week="Friday",
            day_type="Weekday",
            hour=18,
            minute=15,
            time_period="Evening",
            is_peak_period=1,
            train_type="Express",
            train_priority=1,
            disruption_type=disruption_type,
            disruption_duration_minutes=60,
            delay_minutes=20,
            affected_train_count=2,
        )

        scenario_df = pd.DataFrame(
            [scenario]
        )

        row = {
            "disruption_type": disruption_type
        }

        for model_name, pipeline in models.items():

            prediction = pipeline.predict(
                scenario_df
            )[0]

            row[model_name] = max(
                0.0,
                float(prediction),
            )

        rows.append(row)

    result = pd.DataFrame(rows)

    print()
    print(
        result.to_string(
            index=False
        )
    )

    return result


def run_candidate_evaluation(models):

    print_section(
        "ALNS-STYLE CANDIDATE EVALUATION"
    )

    print(
        "This test simulates candidate evaluation."
    )

    print(
        "The ML model estimates passenger impact."
    )

    print(
        "ALNS remains the optimization algorithm."
    )

    disruption = create_scenario(
        station_code="MAS",
        station_category="NSG1",
        station_daily_passengers=65000,
        day_of_week="Monday",
        day_type="Weekday",
        hour=8,
        minute=30,
        time_period="Morning",
        is_peak_period=1,
        train_type="Express",
        train_priority=1,
        disruption_type="PLATFORM_CLOSURE",
        disruption_duration_minutes=60,
        delay_minutes=0,
        affected_train_count=5,
    )

    candidates = {
        "Candidate A": {
            **disruption,
            "delay_minutes": 15,
            "affected_train_count": 5,
        },
        "Candidate B": {
            **disruption,
            "delay_minutes": 25,
            "affected_train_count": 3,
        },
        "Candidate C": {
            **disruption,
            "delay_minutes": 40,
            "affected_train_count": 2,
        },
    }

    rows = []

    for candidate_name, candidate in candidates.items():

        candidate_df = pd.DataFrame(
            [candidate]
        )

        row = {
            "candidate": candidate_name
        }

        for model_name, pipeline in models.items():

            prediction = pipeline.predict(
                candidate_df
            )[0]

            row[model_name] = max(
                0.0,
                float(prediction),
            )

        rows.append(row)

    result = pd.DataFrame(rows)

    print()
    print(
        result.to_string(
            index=False
        )
    )

    print()

    for model_name in models.keys():

        ranking = (
            result[
                [
                    "candidate",
                    model_name,
                ]
            ]
            .sort_values(
                by=model_name
            )
            .reset_index(drop=True)
        )

        print(
            f"{model_name} candidate ranking:"
        )

        for index, row in ranking.iterrows():

            print(
                f"  {index + 1}. "
                f"{row['candidate']} "
                f"-> "
                f"{row[model_name]:,.2f}"
            )

        print()

    return result


# ============================================================
# BEHAVIORAL VALIDATION
# ============================================================

def evaluate_behavioral_rules(
    scenario_results,
    disruption_results,
    candidate_results,
):

    print_section(
        "BEHAVIORAL VALIDATION SUMMARY"
    )

    validation_rows = []

    for model_name in MODEL_NAMES:

        passed = 0
        total = 0

        base_value = float(
            scenario_results.loc[
                scenario_results["scenario"]
                == "Base",
                model_name,
            ].iloc[0]
        )

        delay_value = float(
            scenario_results.loc[
                scenario_results["scenario"]
                == "Delay Increased",
                model_name,
            ].iloc[0]
        )

        total += 1

        delay_pass = (
            delay_value > base_value
        )

        if delay_pass:
            passed += 1

        duration_value = float(
            scenario_results.loc[
                scenario_results["scenario"]
                == "Duration Increased",
                model_name,
            ].iloc[0]
        )

        total += 1

        duration_pass = (
            duration_value > base_value
        )

        if duration_pass:
            passed += 1

        train_value = float(
            scenario_results.loc[
                scenario_results["scenario"]
                == "Affected Trains Increased",
                model_name,
            ].iloc[0]
        )

        total += 1

        trains_pass = (
            train_value > base_value
        )

        if trains_pass:
            passed += 1

        peak_value = base_value

        off_peak_value = float(
            scenario_results.loc[
                scenario_results["scenario"]
                == "Off Peak",
                model_name,
            ].iloc[0]
        )

        total += 1

        peak_pass = (
            peak_value > off_peak_value
        )

        if peak_pass:
            passed += 1

        high_demand_value = float(
            scenario_results.loc[
                scenario_results["scenario"]
                == "High Demand Station",
                model_name,
            ].iloc[0]
        )

        low_demand_value = float(
            scenario_results.loc[
                scenario_results["scenario"]
                == "Low Demand Station",
                model_name,
            ].iloc[0]
        )

        total += 1

        demand_pass = (
            high_demand_value
            > low_demand_value
        )

        if demand_pass:
            passed += 1

        candidate_model_values = (
            candidate_results[
                [
                    "candidate",
                    model_name,
                ]
            ]
            .sort_values(
                by=model_name
            )
            .reset_index(drop=True)
        )

        total += 1

        candidate_pass = (
            candidate_model_values.iloc[0][
                "candidate"
            ]
            == "Candidate A"
        )

        if candidate_pass:
            passed += 1

        validation_rows.append(
            {
                "model": model_name,
                "passed": passed,
                "total": total,
                "behavioral_score": (
                    passed / total
                ),
                "delay_test": (
                    "PASS"
                    if delay_pass
                    else "FAIL"
                ),
                "duration_test": (
                    "PASS"
                    if duration_pass
                    else "FAIL"
                ),
                "affected_trains_test": (
                    "PASS"
                    if trains_pass
                    else "FAIL"
                ),
                "peak_test": (
                    "PASS"
                    if peak_pass
                    else "FAIL"
                ),
                "demand_test": (
                    "PASS"
                    if demand_pass
                    else "FAIL"
                ),
                "candidate_test": (
                    "PASS"
                    if candidate_pass
                    else "FAIL"
                ),
            }
        )

    result = pd.DataFrame(
        validation_rows
    )

    print()
    print(
        result.to_string(
            index=False
        )
    )

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    print_section(
        "PASSENGER IMPACT - MULTI-MODEL EVALUATION"
    )

    print(
        f"Random Seed       : {SEED}"
    )

    print(
        f"Dataset Directory : {DATASET_DIR}"
    )

    print(
        f"Comparison Models : {COMPARISON_MODEL_DIR}"
    )

    print(
        f"Evaluation Dir    : {EVALUATION_DIR}"
    )

    print(
        f"Final Model       : {FINAL_MODEL_DIR}"
    )

    print(
        f"Target            : {TARGET_COLUMN}"
    )

    # --------------------------------------------------------
    # Check dataset files
    # --------------------------------------------------------

    required_files = [
        TRAIN_FILE,
        VALIDATION_FILE,
        TEST_FILE,
    ]

    for file_path in required_files:

        if not file_path.exists():

            raise FileNotFoundError(
                f"Required dataset file not found:\n"
                f"{file_path}"
            )

    COMPARISON_MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    EVALUATION_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    FINAL_MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Load datasets
    # --------------------------------------------------------

    print_section(
        "LOADING DATASETS"
    )

    train_df = pd.read_csv(
        TRAIN_FILE
    )

    validation_df = pd.read_csv(
        VALIDATION_FILE
    )

    test_df = pd.read_csv(
        TEST_FILE
    )

    print(
        f"Training rows   : {len(train_df):,}"
    )

    print(
        f"Validation rows : {len(validation_df):,}"
    )

    print(
        f"Test rows       : {len(test_df):,}"
    )

    # --------------------------------------------------------
    # Validate datasets
    # --------------------------------------------------------

    print_section(
        "VALIDATING DATASETS"
    )

    validate_columns(
        train_df,
        "Training dataset",
    )

    validate_columns(
        validation_df,
        "Validation dataset",
    )

    validate_columns(
        test_df,
        "Test dataset",
    )

    validate_target(
        train_df,
        "Training dataset",
    )

    validate_target(
        validation_df,
        "Validation dataset",
    )

    validate_target(
        test_df,
        "Test dataset",
    )

    print(
        "Required columns : PASS"
    )

    print(
        "Target values    : PASS"
    )

    # --------------------------------------------------------
    # Prepare data
    # --------------------------------------------------------

    X_train = train_df[
        FEATURE_COLUMNS
    ].copy()

    y_train = train_df[
        TARGET_COLUMN
    ].copy()

    X_validation = validation_df[
        FEATURE_COLUMNS
    ].copy()

    y_validation = validation_df[
        TARGET_COLUMN
    ].copy()

    X_test = test_df[
        FEATURE_COLUMNS
    ].copy()

    y_test = test_df[
        TARGET_COLUMN
    ].copy()

    # --------------------------------------------------------
    # Build models
    # --------------------------------------------------------

    print_section(
        "BUILDING FOUR MODELS"
    )

    models = build_model_pipelines()

    for model_name in models:

        print(
            f"Prepared : {model_name}"
        )

    # --------------------------------------------------------
    # Train and evaluate
    # --------------------------------------------------------

    print_section(
        "STAGE 1 - MODEL TRAINING AND EVALUATION"
    )

    comparison_rows = []

    trained_models = {}

    for model_name, pipeline in models.items():

        print()
        print(
            "-" * 70
        )

        print(
            f"TRAINING: {model_name}"
        )

        print(
            "-" * 70
        )

        (
            validation_metrics,
            test_metrics,
        ) = evaluate_model(
            pipeline,
            X_train,
            y_train,
            X_validation,
            y_validation,
            X_test,
            y_test,
        )

        trained_models[
            model_name
        ] = pipeline

        print(
            "Validation:"
        )

        print(
            f"  MAE  = "
            f"{validation_metrics['MAE']:,.2f}"
        )

        print(
            f"  RMSE = "
            f"{validation_metrics['RMSE']:,.2f}"
        )

        print(
            f"  R²   = "
            f"{validation_metrics['R2']:.4f}"
        )

        print(
            "Test:"
        )

        print(
            f"  MAE  = "
            f"{test_metrics['MAE']:,.2f}"
        )

        print(
            f"  RMSE = "
            f"{test_metrics['RMSE']:,.2f}"
        )

        print(
            f"  R²   = "
            f"{test_metrics['R2']:.4f}"
        )

        comparison_rows.append(
            {
                "model": model_name,
                "validation_MAE": (
                    validation_metrics["MAE"]
                ),
                "validation_RMSE": (
                    validation_metrics["RMSE"]
                ),
                "validation_R2": (
                    validation_metrics["R2"]
                ),
                "test_MAE": (
                    test_metrics["MAE"]
                ),
                "test_RMSE": (
                    test_metrics["RMSE"]
                ),
                "test_R2": (
                    test_metrics["R2"]
                ),
            }
        )

    comparison_df = pd.DataFrame(
        comparison_rows
    )

    # --------------------------------------------------------
    # Sort by test R2
    # --------------------------------------------------------

    comparison_df = (
        comparison_df
        .sort_values(
            by="test_R2",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    print_section(
        "MODEL PERFORMANCE COMPARISON"
    )

    display_df = comparison_df.copy()

    for column in [
        "validation_MAE",
        "validation_RMSE",
        "test_MAE",
        "test_RMSE",
    ]:

        display_df[column] = (
            display_df[column]
            .round(2)
        )

    print()

    print(
        display_df[
            [
                "model",
                "validation_R2",
                "test_R2",
                "test_MAE",
                "test_RMSE",
            ]
        ].to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # Save comparison
    # --------------------------------------------------------

    comparison_path = (
        EVALUATION_DIR
        / "model_comparison.csv"
    )

    comparison_df.to_csv(
        comparison_path,
        index=False,
    )

    print()
    print(
        f"Comparison saved: "
        f"{comparison_path}"
    )

    # --------------------------------------------------------
    # Stage 2 scenario testing
    # --------------------------------------------------------

    scenario_results = (
        run_behavioral_scenarios(
            trained_models
        )
    )

    scenario_path = (
        EVALUATION_DIR
        / "behavioral_scenario_results.csv"
    )

    scenario_results.to_csv(
        scenario_path,
        index=False,
    )

    print()
    print(
        f"Scenario results saved: "
        f"{scenario_path}"
    )

    # --------------------------------------------------------
    # Disruption type testing
    # --------------------------------------------------------

    disruption_results = (
        run_disruption_type_scenarios(
            trained_models
        )
    )

    disruption_path = (
        EVALUATION_DIR
        / "disruption_type_results.csv"
    )

    disruption_results.to_csv(
        disruption_path,
        index=False,
    )

    print()
    print(
        f"Disruption results saved: "
        f"{disruption_path}"
    )

    # --------------------------------------------------------
    # ALNS-style candidate evaluation
    # --------------------------------------------------------

    candidate_results = (
        run_candidate_evaluation(
            trained_models
        )
    )

    candidate_path = (
        EVALUATION_DIR
        / "candidate_evaluation_results.csv"
    )

    candidate_results.to_csv(
        candidate_path,
        index=False,
    )

    print()
    print(
        f"Candidate results saved: "
        f"{candidate_path}"
    )

    # --------------------------------------------------------
    # Behavioral validation
    # --------------------------------------------------------

    behavioral_validation = (
        evaluate_behavioral_rules(
            scenario_results,
            disruption_results,
            candidate_results,
        )
    )

    behavioral_path = (
        EVALUATION_DIR
        / "behavioral_validation_results.csv"
    )

    behavioral_validation.to_csv(
        behavioral_path,
        index=False,
    )

    print()
    print(
        f"Behavioral validation saved: "
        f"{behavioral_path}"
    )

    # --------------------------------------------------------
    # Combined evaluation summary
    # --------------------------------------------------------

    final_comparison = comparison_df.copy()

    behavioral_scores = (
        behavioral_validation[
            [
                "model",
                "passed",
                "total",
                "behavioral_score",
            ]
        ]
    )

    final_comparison = final_comparison.merge(
        behavioral_scores,
        on="model",
        how="left",
    )

    # --------------------------------------------------------
    # Ranking indicators
    # --------------------------------------------------------

    final_comparison[
        "R2_rank"
    ] = (
        final_comparison[
            "test_R2"
        ]
        .rank(
            ascending=False,
            method="min",
        )
        .astype(int)
    )

    final_comparison[
        "MAE_rank"
    ] = (
        final_comparison[
            "test_MAE"
        ]
        .rank(
            ascending=True,
            method="min",
        )
        .astype(int)
    )

    final_comparison[
        "RMSE_rank"
    ] = (
        final_comparison[
            "test_RMSE"
        ]
        .rank(
            ascending=True,
            method="min",
        )
        .astype(int)
    )

    final_comparison[
        "behavior_rank"
    ] = (
        final_comparison[
            "behavioral_score"
        ]
        .rank(
            ascending=False,
            method="min",
        )
        .astype(int)
    )

    # --------------------------------------------------------
    # Combined rank
    # --------------------------------------------------------

    final_comparison[
        "combined_rank_score"
    ] = (
        final_comparison[
            "R2_rank"
        ]
        + final_comparison[
            "MAE_rank"
        ]
        + final_comparison[
            "RMSE_rank"
        ]
        + final_comparison[
            "behavior_rank"
        ]
    )

    final_comparison = (
        final_comparison
        .sort_values(
            by=[
                "combined_rank_score",
                "R2_rank",
            ],
            ascending=[
                True,
                True,
            ],
        )
        .reset_index(drop=True)
    )

    final_comparison[
        "overall_rank"
    ] = (
        np.arange(
            1,
            len(final_comparison) + 1,
        )
    )

    # --------------------------------------------------------
    # Final comparison output
    # --------------------------------------------------------

    print_section(
        "FINAL MODEL COMPARISON"
    )

    final_display_columns = [
        "overall_rank",
        "model",
        "test_R2",
        "test_MAE",
        "test_RMSE",
        "behavioral_score",
        "combined_rank_score",
    ]

    print()

    print(
        final_comparison[
            final_display_columns
        ].to_string(
            index=False
        )
    )

    final_comparison_path = (
        EVALUATION_DIR
        / "final_model_comparison.csv"
    )

    final_comparison.to_csv(
        final_comparison_path,
        index=False,
    )

    print()
    print(
        f"Final comparison saved: "
        f"{final_comparison_path}"
    )

    # --------------------------------------------------------
    # Save trained models
    # --------------------------------------------------------

    print_section(
        "SAVING TRAINED MODELS"
    )

    for model_name, pipeline in (
        trained_models.items()
    ):

        if model_name == "Random Forest":

            model_path = (
                COMPARISON_MODEL_DIR
                / "random_forest_model.joblib"
            )

        elif model_name == "Extra Trees":

            model_path = (
                COMPARISON_MODEL_DIR
                / "extra_trees_model.joblib"
            )

        elif model_name == "Gradient Boosting":

            model_path = (
                COMPARISON_MODEL_DIR
                / "gradient_boosting_model.joblib"
            )

        elif model_name == "HistGradientBoosting":

            model_path = (
                FINAL_MODEL_DIR
                / "passenger_impact_model.joblib"
            )

        else:

            raise ValueError(
                f"Unknown model name: {model_name}"
            )

        joblib.dump(
            pipeline,
            model_path,
        )

        print(
            f"{model_name:<25} -> "
            f"{model_path}"
        )

    # --------------------------------------------------------
    # Save final model preprocessor separately
    # --------------------------------------------------------

    final_pipeline = trained_models[
        FINAL_MODEL_NAME
    ]

    final_preprocessor = (
        final_pipeline.named_steps[
            "preprocessor"
        ]
    )

    preprocessor_path = (
        FINAL_MODEL_DIR
        / "passenger_impact_preprocessor.joblib"
    )

    joblib.dump(
        final_preprocessor,
        preprocessor_path,
    )

    print(
        f"{'Final preprocessor':<25} -> "
        f"{preprocessor_path}"
    )

    # --------------------------------------------------------
    # Save final model metadata
    # --------------------------------------------------------

    final_model_metrics = (
        comparison_df[
            comparison_df["model"]
            == FINAL_MODEL_NAME
        ]
        .iloc[0]
        .to_dict()
    )

    final_behavioral_metrics = (
        behavioral_validation[
            behavioral_validation["model"]
            == FINAL_MODEL_NAME
        ]
        .iloc[0]
        .to_dict()
    )

    model_metadata = {
        "model_version": "v1.0-passenger-impact-hgb",
        "model_name": FINAL_MODEL_NAME,
        "model_type": (
            "HistGradientBoostingRegressor"
        ),
        "target": TARGET_COLUMN,
        "random_seed": SEED,
        "feature_columns": FEATURE_COLUMNS,
        "categorical_features": (
            CATEGORICAL_FEATURES
        ),
        "numeric_features": (
            NUMERIC_FEATURES
        ),
        "training_rows": int(
            len(train_df)
        ),
        "validation_rows": int(
            len(validation_df)
        ),
        "test_rows": int(
            len(test_df)
        ),
        "test_metrics": {
            "MAE": float(
                final_model_metrics[
                    "test_MAE"
                ]
            ),
            "RMSE": float(
                final_model_metrics[
                    "test_RMSE"
                ]
            ),
            "R2": float(
                final_model_metrics[
                    "test_R2"
                ]
            ),
        },
        "validation_metrics": {
            "MAE": float(
                final_model_metrics[
                    "validation_MAE"
                ]
            ),
            "RMSE": float(
                final_model_metrics[
                    "validation_RMSE"
                ]
            ),
            "R2": float(
                final_model_metrics[
                    "validation_R2"
                ]
            ),
        },
        "behavioral_validation": {
            "passed": int(
                final_behavioral_metrics[
                    "passed"
                ]
            ),
            "total": int(
                final_behavioral_metrics[
                    "total"
                ]
            ),
            "behavioral_score": float(
                final_behavioral_metrics[
                    "behavioral_score"
                ]
            ),
        },
        "intended_use": (
            "Passenger impact estimation for "
            "ALNS candidate evaluation."
        ),
        "optimization_role": (
            "The ML model estimates passenger impact. "
            "ALNS remains the timetable optimization "
            "algorithm."
        ),
        "dataset_note": (
            "The passenger impact training target is "
            "based on the controlled synthetic "
            "passenger-impact dataset generated from "
            "station passenger-demand baselines and "
            "validated timetable characteristics. "
            "It is not historical passenger-delay data."
        ),
        "selection_note": (
            "HistGradientBoosting is finalized as the "
            "Phase 1 Passenger Impact model based on "
            "quantitative test metrics and behavioral "
            "validation."
        ),
    }

    metadata_path = (
        FINAL_MODEL_DIR
        / "model_metadata.json"
    )

    with open(
        metadata_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            model_metadata,
            file,
            indent=4,
        )

    print(
        f"{'Model metadata':<25} -> "
        f"{metadata_path}"
    )

    # --------------------------------------------------------
    # Save evaluation summary JSON
    # --------------------------------------------------------

    summary = {
        "evaluation_version":
            "v1.0-four-model-comparison",

        "random_seed":
            SEED,

        "target":
            TARGET_COLUMN,

        "models":
            MODEL_NAMES,

        "final_model":
            FINAL_MODEL_NAME,

        "training_rows":
            int(len(train_df)),

        "validation_rows":
            int(len(validation_df)),

        "test_rows":
            int(len(test_df)),

        "feature_columns":
            FEATURE_COLUMNS,

        "evaluation_metrics": {
            "model_performance": [
                {
                    key: (
                        float(value)
                        if isinstance(
                            value,
                            (np.floating, float)
                        )
                        else int(value)
                        if isinstance(
                            value,
                            (np.integer, int)
                        )
                        else value
                    )
                    for key, value in row.items()
                }
                for row in comparison_df.to_dict(
                    orient="records"
                )
            ],
            "behavioral_validation": [
                {
                    key: (
                        float(value)
                        if isinstance(
                            value,
                            (np.floating, float)
                        )
                        else int(value)
                        if isinstance(
                            value,
                            (np.integer, int)
                        )
                        else value
                    )
                    for key, value in row.items()
                }
                for row in behavioral_validation.to_dict(
                    orient="records"
                )
            ],
        },

        "selection_method": (
            "HistGradientBoosting was finalized after "
            "comparison of regression metrics and "
            "behavioral scenario validation."
        ),

        "important_note": (
            "R2 is a regression metric and should not "
            "be interpreted as percentage accuracy. "
            "The reported metrics apply to the controlled "
            "synthetic passenger-impact test dataset."
        ),

        "intended_use": (
            "Passenger impact estimation for ALNS "
            "candidate evaluation."
        ),
    }

    summary_path = (
        EVALUATION_DIR
        / "multi_model_evaluation_summary.json"
    )

    with open(
        summary_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            summary,
            file,
            indent=4,
        )

    print()
    print(
        f"Evaluation summary saved: "
        f"{summary_path}"
    )

    # --------------------------------------------------------
    # Final message
    # --------------------------------------------------------

    print_section(
        "MULTI-MODEL EVALUATION COMPLETE"
    )

    print(
        "Four models were trained and evaluated."
    )

    print(
        "Regression metrics were compared."
    )

    print(
        "Behavioral scenarios were tested."
    )

    print(
        "ALNS-style candidate evaluation was tested."
    )

    print()
    print(
        f"Final Passenger Impact Model: "
        f"{FINAL_MODEL_NAME}"
    )

    print(
        "Final model and preprocessor saved "
        "under final_model/."
    )

    print(
        "Comparison models saved under "
        "comparison_models/."
    )

    print(
        "Evaluation outputs saved under "
        "evaluation/."
    )

    print()
    print(
        "The Passenger Impact model estimates "
        "passenger impact for ALNS candidate "
        "evaluation."
    )

    print(
        "ALNS remains the timetable optimization "
        "algorithm."
    )

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()