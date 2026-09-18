#python
"""
Manual ALNS-Style Passenger Impact ML Test
==========================================

Purpose:
    Compare all four trained Passenger Impact ML models
    using the same manually created ALNS-style candidates.

Flow:

    Manual disruption
            ↓
    Candidate A / B / C
            ↓
    Four Passenger Impact ML Models
            ↓
    Predicted passenger-delay minutes
            ↓
    Candidate comparison
            ↓
    Model comparison

Models tested:
    1. Random Forest
    2. Extra Trees
    3. Gradient Boosting
    4. HistGradientBoosting

Important:
    This does NOT run the ALNS optimizer.

    It manually simulates the candidate-evaluation stage.

    The real ALNS will later generate feasible timetable
    recovery candidates and pass each candidate through
    the selected Passenger Impact model.

    Lower predicted passenger-delay minutes means lower
    passenger-impact objective for this test.
"""

from pathlib import Path

import joblib
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PASSENGER_ML_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "passenger_ml"
)

COMPARISON_MODEL_DIRECTORY = (
    PASSENGER_ML_DIRECTORY
    / "comparison_models"
)

FINAL_MODEL_DIRECTORY = (
    PASSENGER_ML_DIRECTORY
    / "final_model"
)


# ============================================================
# MODEL PATHS
# ============================================================

MODEL_PATHS = {
    "Random Forest": (
        COMPARISON_MODEL_DIRECTORY
        / "random_forest_model.joblib"
    ),
    "Extra Trees": (
        COMPARISON_MODEL_DIRECTORY
        / "extra_trees_model.joblib"
    ),
    "Gradient Boosting": (
        COMPARISON_MODEL_DIRECTORY
        / "gradient_boosting_model.joblib"
    ),
    "HistGradientBoosting": (
        FINAL_MODEL_DIRECTORY
        / "passenger_impact_model.joblib"
    ),
}


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
# DISPLAY HELPERS
# ============================================================

def line():
    print("-" * 90)


def get_prediction(model, scenario):
    """
    Run one trained ML model for one candidate.
    """

    df = pd.DataFrame([scenario])

    features = df[FEATURE_COLUMNS]

    prediction = model.predict(features)[0]

    return max(0.0, float(prediction))


def print_candidate_details(candidate_name, scenario):
    """
    Display candidate input values.
    """

    print()
    print(candidate_name)
    line()

    print(
        f"Delay                 : "
        f"{scenario['delay_minutes']} minutes"
    )

    print(
        f"Affected trains       : "
        f"{scenario['affected_train_count']}"
    )

    print(
        f"Disruption duration   : "
        f"{scenario['disruption_duration_minutes']} minutes"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 90)
    print("FOUR-MODEL MANUAL ALNS-STYLE PASSENGER IMPACT ML TEST")
    print("=" * 90)

    print()
    print(
        "This test manually simulates 3 ALNS recovery candidates."
    )

    print(
        "All four trained Passenger Impact models will evaluate"
        " the same candidates."
    )

    # ========================================================
    # CHECK MODEL FILES
    # ========================================================

    print()
    print("=" * 90)
    print("MODEL FILE CHECK")
    print("=" * 90)

    missing_models = []

    for model_name, model_path in MODEL_PATHS.items():

        print()
        print(f"{model_name:<25}: {model_path}")

        if model_path.exists():
            print("Status                    : FOUND")
        else:
            print("Status                    : NOT FOUND")
            missing_models.append(model_name)

    if missing_models:

        raise FileNotFoundError(
            "\nThe following model files are missing:\n"
            + "\n".join(
                f"- {name}"
                for name in missing_models
            )
        )

    # ========================================================
    # LOAD ALL FOUR MODELS
    # ========================================================

    print()
    print("=" * 90)
    print("LOADING FOUR PASSENGER IMPACT MODELS")
    print("=" * 90)

    models = {}

    for model_name, model_path in MODEL_PATHS.items():

        print()
        print(f"Loading {model_name}...")

        models[model_name] = joblib.load(model_path)

        print("Loaded successfully.")

    # ========================================================
    # MANUAL DISRUPTION INPUT
    # ========================================================

    print()
    print("=" * 90)
    print("DISRUPTION INPUT")
    print("=" * 90)

    # --------------------------------------------------------
    # Same disruption used in the previous ALNS-style test.
    # --------------------------------------------------------

    disruption = {
        "station_code": "MAS",
        "station_category": "NSG1",
        "station_daily_passengers": 65000,
        "day_of_week": "Monday",
        "day_type": "Weekday",
        "hour": 8,
        "minute": 30,
        "time_period": "Morning peak",
        "is_peak_period": 1,
        "train_type": "Express",
        "train_priority": 1,
        "disruption_type": "PLATFORM_CLOSURE",
        "disruption_duration_minutes": 60,
    }

    print(
        f"Station              : "
        f"{disruption['station_code']}"
    )

    print(
        f"Station demand/day   : "
        f"{disruption['station_daily_passengers']:,}"
    )

    print(
        f"Date type            : "
        f"{disruption['day_type']}"
    )

    print(
        f"Day                  : "
        f"{disruption['day_of_week']}"
    )

    print(
        f"Time                 : "
        f"{disruption['hour']:02d}:"
        f"{disruption['minute']:02d}"
    )

    print(
        f"Time period          : "
        f"{disruption['time_period']}"
    )

    print(
        f"Disruption           : "
        f"{disruption['disruption_type']}"
    )

    print(
        f"Disruption duration  : "
        f"{disruption['disruption_duration_minutes']} minutes"
    )

    # ========================================================
    # MANUAL ALNS CANDIDATES
    # ========================================================

    print()
    print("=" * 90)
    print("MANUAL ALNS CANDIDATES")
    print("=" * 90)

    print(
        """
These represent three hypothetical recovery solutions
generated by ALNS.

Only candidate-level values that affect passenger impact
are changed here.
"""
    )

    # --------------------------------------------------------
    # Candidate A
    # --------------------------------------------------------

    candidate_a = disruption.copy()

    candidate_a.update(
        {
            "delay_minutes": 15,
            "affected_train_count": 5,
        }
    )

    # --------------------------------------------------------
    # Candidate B
    # --------------------------------------------------------

    candidate_b = disruption.copy()

    candidate_b.update(
        {
            "delay_minutes": 25,
            "affected_train_count": 3,
        }
    )

    # --------------------------------------------------------
    # Candidate C
    # --------------------------------------------------------

    candidate_c = disruption.copy()

    candidate_c.update(
        {
            "delay_minutes": 40,
            "affected_train_count": 2,
        }
    )

    candidates = {
        "A": candidate_a,
        "B": candidate_b,
        "C": candidate_c,
    }

    # ========================================================
    # DISPLAY CANDIDATES
    # ========================================================

    for candidate_name, scenario in candidates.items():

        print_candidate_details(
            f"CANDIDATE {candidate_name}",
            scenario,
        )

    # ========================================================
    # RUN ALL FOUR MODELS
    # ========================================================

    print()
    print("=" * 90)
    print("RUNNING FOUR MODELS")
    print("=" * 90)

    all_predictions = []

    for model_name, model in models.items():

        print()
        print(f"MODEL: {model_name}")
        line()

        for candidate_name, scenario in candidates.items():

            prediction = get_prediction(
                model,
                scenario,
            )

            all_predictions.append(
                {
                    "model": model_name,
                    "candidate": candidate_name,
                    "delay_minutes": scenario["delay_minutes"],
                    "affected_train_count": scenario[
                        "affected_train_count"
                    ],
                    "predicted_passenger_delay_minutes": prediction,
                }
            )

            print(
                f"Candidate {candidate_name} -> "
                f"{prediction:,.2f} "
                f"passenger-delay minutes"
            )

    # ========================================================
    # CREATE RESULTS DATAFRAME
    # ========================================================

    results = pd.DataFrame(all_predictions)

    # ========================================================
    # MODEL-BY-CANDIDATE COMPARISON
    # ========================================================

    print()
    print("=" * 90)
    print("PASSENGER IMPACT PREDICTIONS BY MODEL")
    print("=" * 90)

    pivot = results.pivot(
        index="candidate",
        columns="model",
        values="predicted_passenger_delay_minutes",
    )

    pivot = pivot[
        [
            "Random Forest",
            "Extra Trees",
            "Gradient Boosting",
            "HistGradientBoosting",
        ]
    ]

    print()
    print(pivot.to_string(float_format=lambda x: f"{x:,.2f}"))

    # ========================================================
    # FIND BEST CANDIDATE FOR EACH MODEL
    # ========================================================

    print()
    print("=" * 90)
    print("BEST CANDIDATE BY EACH MODEL")
    print("=" * 90)

    model_best_results = []

    for model_name in models.keys():

        model_results = results[
            results["model"] == model_name
        ].sort_values(
            by="predicted_passenger_delay_minutes",
            ascending=True,
        ).reset_index(drop=True)

        best = model_results.iloc[0]

        model_best_results.append(
            {
                "model": model_name,
                "best_candidate": best["candidate"],
                "predicted_passenger_delay_minutes": best[
                    "predicted_passenger_delay_minutes"
                ],
                "delay_minutes": best["delay_minutes"],
                "affected_train_count": best[
                    "affected_train_count"
                ],
            }
        )

        print()
        print(f"Model                 : {model_name}")
        print(
            f"Best candidate        : "
            f"{best['candidate']}"
        )
        print(
            f"Predicted passenger   : "
            f"{best['predicted_passenger_delay_minutes']:,.2f}"
        )
        print(
            f"Train delay           : "
            f"{int(best['delay_minutes'])} minutes"
        )
        print(
            f"Affected trains       : "
            f"{int(best['affected_train_count'])}"
        )

    # ========================================================
    # CANDIDATE RANKING FOR EACH MODEL
    # ========================================================

    print()
    print("=" * 90)
    print("CANDIDATE RANKING FOR EACH MODEL")
    print("=" * 90)

    ranking_results = []

    for model_name in models.keys():

        model_results = results[
            results["model"] == model_name
        ].sort_values(
            by="predicted_passenger_delay_minutes",
            ascending=True,
        ).reset_index(drop=True)

        model_results["rank"] = range(
            1,
            len(model_results) + 1,
        )

        print()
        print(model_name)
        line()

        for _, row in model_results.iterrows():

            print(
                f"Rank {int(row['rank'])} -> "
                f"Candidate {row['candidate']} -> "
                f"{row['predicted_passenger_delay_minutes']:,.2f}"
            )

            ranking_results.append(
                {
                    "model": model_name,
                    "candidate": row["candidate"],
                    "rank": int(row["rank"]),
                    "predicted_passenger_delay_minutes": row[
                        "predicted_passenger_delay_minutes"
                    ],
                }
            )

    # ========================================================
    # BEHAVIORAL CHECK
    # ========================================================

    print()
    print("=" * 90)
    print("ALNS-STYLE BEHAVIORAL CHECK")
    print("=" * 90)

    print(
        """
Expected relationship:

Candidate A:
    Lower delay
    Higher affected trains

Candidate B:
    Medium delay
    Medium affected trains

Candidate C:
    Higher delay
    Lower affected trains

The test checks whether each model identifies
Candidate A as having the lowest predicted
passenger impact.
"""
    )

    behavioral_results = []

    for model_name in models.keys():

        model_results = results[
            results["model"] == model_name
        ].sort_values(
            by="predicted_passenger_delay_minutes",
            ascending=True,
        ).reset_index(drop=True)

        predicted_order = list(
            model_results["candidate"]
        )

        candidate_test = (
            predicted_order == ["A", "B", "C"]
        )

        behavioral_results.append(
            {
                "model": model_name,
                "expected_order": "A > B > C",
                "predicted_order": " > ".join(
                    predicted_order
                ),
                "candidate_test": (
                    "PASS"
                    if candidate_test
                    else "FAIL"
                ),
            }
        )

        print()
        print(f"Model: {model_name}")

        print(
            f"Predicted order      : "
            f"{' > '.join(predicted_order)}"
        )

        print(
            f"Expected order       : A > B > C"
        )

        print(
            f"Candidate test       : "
            f"{'PASS' if candidate_test else 'FAIL'}"
        )

    # ========================================================
    # FINAL MODEL COMPARISON
    # ========================================================

    print()
    print("=" * 90)
    print("FINAL FOUR-MODEL ALNS-STYLE COMPARISON")
    print("=" * 90)

    final_comparison = pd.DataFrame(
        model_best_results
    )

    print()

    print(
        final_comparison[
            [
                "model",
                "best_candidate",
                "predicted_passenger_delay_minutes",
                "delay_minutes",
                "affected_train_count",
            ]
        ].to_string(
            index=False,
            float_format=lambda x: f"{x:,.2f}",
        )
    )

    # ========================================================
    # SAVE RESULTS
    # ========================================================

    output_directory = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "passenger_ml"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_predictions_path = (
        output_directory
        / "alns_style_four_model_predictions.csv"
    )

    rankings_path = (
        output_directory
        / "alns_style_four_model_rankings.csv"
    )

    behavioral_path = (
        output_directory
        / "alns_style_four_model_behavioral_validation.csv"
    )

    final_comparison_path = (
        output_directory
        / "alns_style_four_model_comparison.csv"
    )

    results.to_csv(
        all_predictions_path,
        index=False,
    )

    pd.DataFrame(
        ranking_results
    ).to_csv(
        rankings_path,
        index=False,
    )

    pd.DataFrame(
        behavioral_results
    ).to_csv(
        behavioral_path,
        index=False,
    )

    final_comparison.to_csv(
        final_comparison_path,
        index=False,
    )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print("=" * 90)
    print("RESULT FILES SAVED")
    print("=" * 90)

    print()
    print(all_predictions_path)

    print()
    print(rankings_path)

    print()
    print(behavioral_path)

    print()
    print(final_comparison_path)

    # ========================================================
    # IMPORTANT NOTE
    # ========================================================

    print()
    print("=" * 90)
    print("IMPORTANT")
    print("=" * 90)

    print(
        """
This test demonstrates only the Passenger Impact
evaluation part of ALNS.

The real ALNS will generate candidate timetables by
changing train/platform/resource assignments.

For each feasible candidate:

    Candidate timetable
            ↓
    Extract ML features
            ↓
    Passenger Impact Model
            ↓
    Predicted passenger-delay minutes
            ↓
    Candidate objective/evaluation

The final ALNS objective will eventually combine:

    Train delay
    +
    Passenger impact
    +
    Feasibility/resource constraints

The model selected from this comparison will be used
as the Passenger Impact estimator inside the ALNS
candidate evaluation stage.

This script does NOT run the actual ALNS optimizer.
"""
    )

    print("=" * 90)
    print("FOUR-MODEL ALNS-STYLE ML TEST COMPLETE")
    print("=" * 90)


if __name__ == "__main__":
    main()

