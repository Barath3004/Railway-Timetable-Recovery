from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

import joblib
import pandas as pd

from .alns_solution import ALNSSolution, TimetableRecord


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "database"
    / "railway_recovery.db"
)

MODEL_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "passenger_ml"
    / "final_model"
    / "passenger_impact_model.joblib"
)

PASSENGER_DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "passenger"
    / "project_station_passenger_data.csv"
)


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


class CandidateEvaluator:
    """
    Evaluate a complete ALNS timetable candidate.

    Responsibilities:
    1. Calculate positive train delay.
    2. Estimate passenger impact using the trained ML model.
    3. Check complete-solution feasibility.
    4. Calculate a common normalized objective.

    Lower objective values represent better candidates.

    A candidate is expected to represent a COMPLETE timetable
    solution for the active disruption.
    """

    def __init__(
        self,
        db_path: Path | str = DATABASE_PATH,
        model_path: Path | str = MODEL_PATH,
        passenger_data_path: Path | str = PASSENGER_DATA_PATH,
        disruption=None,
        delay_weight: float = 0.5,
        passenger_weight: float = 0.5,
    ) -> None:

        if delay_weight < 0:
            raise ValueError(
                "delay_weight must be >= 0."
            )

        if passenger_weight < 0:
            raise ValueError(
                "passenger_weight must be >= 0."
            )

        if (
            delay_weight == 0
            and passenger_weight == 0
        ):
            raise ValueError(
                "At least one objective weight must be > 0."
            )

        self.db_path = Path(db_path)
        self.model_path = Path(model_path)
        self.passenger_data_path = Path(
            passenger_data_path
        )

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database not found: {self.db_path}"
            )

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Passenger impact model not found: "
                f"{self.model_path}"
            )

        if not self.passenger_data_path.exists():
            raise FileNotFoundError(
                f"Passenger demand data not found: "
                f"{self.passenger_data_path}"
            )

        if disruption is None:
            raise ValueError(
                "An active disruption must be provided."
            )

        self.disruption = disruption

        self.delay_weight = float(
            delay_weight
        )

        self.passenger_weight = float(
            passenger_weight
        )

        self.model = joblib.load(
            self.model_path
        )

        self.passenger_lookup = (
            self._load_passenger_lookup()
        )

        self.train_lookup = (
            self._load_train_lookup()
        )

        self.delay_reference = (
            self._calculate_disruption_duration()
        )

        self.passenger_reference = (
            self._calculate_passenger_reference()
        )

    # ========================================================
    # DATABASE LOOKUPS
    # ========================================================

    def _load_passenger_lookup(
        self,
    ) -> dict[str, dict[str, object]]:
        """
        Load station passenger information.

        The source is the same station passenger-demand
        dataset used for the project's passenger ML work.
        """

        df = pd.read_csv(
            self.passenger_data_path
        )

        required_columns = {
            "station_code",
            "category",
            "daily_passengers",
        }

        missing = (
            required_columns
            - set(df.columns)
        )

        if missing:
            raise ValueError(
                "Passenger dataset is missing "
                f"columns: {sorted(missing)}"
            )

        lookup: dict[
            str,
            dict[str, object],
        ] = {}

        for _, row in df.iterrows():

            station_code = str(
                row["station_code"]
            ).strip()

            if not station_code:
                continue

            category = str(
                row["category"]
            ).strip()

            daily_passengers = float(
                row["daily_passengers"]
            )

            lookup[station_code] = {
                "category": category,
                "daily_passengers": (
                    daily_passengers
                ),
            }

        return lookup

    def _load_train_lookup(
        self,
    ) -> dict[str, dict[str, object]]:
        """
        Load train type and priority from the
        authoritative trains table.
        """

        connection = sqlite3.connect(
            self.db_path
        )

        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    train_number,
                    train_type,
                    priority
                FROM trains
                """
            )

            rows = cursor.fetchall()

        finally:
            connection.close()

        lookup: dict[
            str,
            dict[str, object],
        ] = {}

        for (
            train_number,
            train_type,
            priority,
        ) in rows:

            lookup[str(train_number)] = {
                "train_type": str(
                    train_type
                ),
                "priority": int(
                    priority
                ),
            }

        return lookup

    def _get_station_category(
        self,
        station_code: str,
    ) -> str:
        """
        Get the actual station category used by
        the passenger ML model.
        """

        station = self.passenger_lookup.get(
            station_code
        )

        if station is None:
            raise KeyError(
                "Passenger information not found "
                f"for station: {station_code}"
            )

        return str(
            station["category"]
        )

    def _get_station_daily_passengers(
        self,
        station_code: str,
    ) -> float:
        """
        Get actual station daily passenger demand.
        """

        station = self.passenger_lookup.get(
            station_code
        )

        if station is None:
            raise KeyError(
                "Passenger information not found "
                f"for station: {station_code}"
            )

        return float(
            station["daily_passengers"]
        )

    def _get_train_type(
        self,
        record: TimetableRecord,
    ) -> str:
        """
        Get train type from the authoritative
        train master database.
        """

        train = self.train_lookup.get(
            record.train_number
        )

        if train is None:
            raise KeyError(
                "Train information not found "
                f"for train: {record.train_number}"
            )

        return str(
            train["train_type"]
        )

    def _get_train_priority(
        self,
        record: TimetableRecord,
    ) -> int:
        """
        Get train priority from the authoritative
        train master database.
        """

        train = self.train_lookup.get(
            record.train_number
        )

        if train is None:
            raise KeyError(
                "Train information not found "
                f"for train: {record.train_number}"
            )

        return int(
            train["priority"]
        )

    # ========================================================
    # DISRUPTION HELPERS
    # ========================================================

    def _get_disruption_type(self) -> str:
        """
        Get the active disruption type.
        """

        value = getattr(
            self.disruption,
            "disruption_type",
            None,
        )

        if value is None:
            raise AttributeError(
                "Disruption object must contain "
                "'disruption_type'."
            )

        return str(value)

    def _get_disruption_duration(self) -> float:
        """
        Calculate active disruption duration in minutes.
        Handles midnight crossing.
        """

        start_time = getattr(
            self.disruption,
            "start_time",
            None,
        )

        end_time = getattr(
            self.disruption,
            "end_time",
            None,
        )

        if (
            start_time is None
            or end_time is None
        ):
            raise AttributeError(
                "Disruption object must contain "
                "'start_time' and 'end_time'."
            )

        start_minutes = (
            self._time_to_minutes(
                start_time
            )
        )

        end_minutes = (
            self._time_to_minutes(
                end_time
            )
        )

        if (
            start_minutes is None
            or end_minutes is None
        ):
            raise ValueError(
                "Invalid disruption start/end time."
            )

        duration = (
            end_minutes
            - start_minutes
        )

        if duration < 0:
            duration += 1440

        if duration <= 0:
            raise ValueError(
                "Disruption duration must be > 0."
            )

        return float(duration)

    def _calculate_disruption_duration(
        self,
    ) -> float:
        """
        Fixed reference scale for train delay.

        All candidates for the same disruption use
        the same delay reference.
        """

        return max(
            1.0,
            self._get_disruption_duration(),
        )

    def _calculate_passenger_reference(
        self,
    ) -> float:
        """
        Calculate a common passenger-impact reference.

        The reference represents approximate passenger
        exposure during the disruption window:

            daily passengers
            × disruption duration / 1440

        It is calculated from the stations involved
        in the active disruption.

        This reference is fixed for all candidates of
        the same disruption.
        """

        station_codes = set()

        station_code = getattr(
            self.disruption,
            "station_code",
            None,
        )

        if station_code:
            station_codes.add(
                str(station_code)
            )

        total_daily_passengers = 0.0

        for code in station_codes:

            total_daily_passengers += (
                self._get_station_daily_passengers(
                    code
                )
            )

        if total_daily_passengers <= 0:
            return 1.0

        duration = (
            self._get_disruption_duration()
        )

        exposure = (
            total_daily_passengers
            * duration
            / 1440.0
        )

        return max(
            1.0,
            float(exposure),
        )

    # ========================================================
    # TIME HELPERS
    # ========================================================

    @staticmethod
    def _time_to_minutes(
        time_value: str | None,
    ) -> int | None:
        """
        Convert HH:MM or HH:MM:SS into minutes
        from midnight.
        """

        if not time_value:
            return None

        parts = str(
            time_value
        ).split(":")

        if len(parts) < 2:
            raise ValueError(
                f"Invalid time value: {time_value}"
            )

        hour = int(parts[0])
        minute = int(parts[1])

        return (
            hour * 60
            + minute
        )

    @classmethod
    def _calculate_positive_delay(
        cls,
        original_time: str | None,
        candidate_time: str | None,
    ) -> float:
        """
        Calculate positive delay.

        Handles midnight crossing.

        Example:
            Original: 23:55
            Candidate: 00:10

            Delay = 15 minutes
        """

        original_minutes = (
            cls._time_to_minutes(
                original_time
            )
        )

        candidate_minutes = (
            cls._time_to_minutes(
                candidate_time
            )
        )

        if (
            original_minutes is None
            or candidate_minutes is None
        ):
            return 0.0

        difference = (
            candidate_minutes
            - original_minutes
        )

        if difference < -720:
            difference += 1440

        return max(
            0.0,
            float(difference),
        )

    # ========================================================
    # TRAIN DELAY
    # ========================================================

    @classmethod
    def calculate_record_delay(
        cls,
        record: TimetableRecord,
    ) -> float:
        """
        Calculate delay for one timetable record.

        Departure delay is preferred.

        Arrival and departure are NOT added together,
        preventing double-counting.
        """

        if (
            record.original_departure is not None
            and record.departure is not None
        ):
            return cls._calculate_positive_delay(
                record.original_departure,
                record.departure,
            )

        if (
            record.original_arrival is not None
            and record.arrival is not None
        ):
            return cls._calculate_positive_delay(
                record.original_arrival,
                record.arrival,
            )

        return 0.0

    @classmethod
    def calculate_total_delay(
        cls,
        records: Iterable[TimetableRecord],
    ) -> float:
        """
        Calculate total positive delay.
        """

        total_delay = 0.0

        for record in records:
            total_delay += (
                cls.calculate_record_delay(
                    record
                )
            )

        return float(
            total_delay
        )

    # ========================================================
    # CHANGED RECORDS
    # ========================================================

    @staticmethod
    def get_changed_records(
        solution: ALNSSolution,
    ) -> list[TimetableRecord]:
        """
        Return records whose timetable or resource
        assignment differs from the original.
        """

        changed_records = []

        for record in solution.records.values():

            timetable_changed = (
                record.arrival
                != record.original_arrival
                or record.departure
                != record.original_departure
            )

            resource_changed = (
                record.resource_id
                != record.original_resource_id
                or record.platform_number
                != record.original_platform_number
            )

            if (
                timetable_changed
                or resource_changed
            ):
                changed_records.append(
                    record
                )

        return changed_records

    # ========================================================
    # TIME FEATURES FOR ML
    # ========================================================

    @staticmethod
    def _get_time_features(
        record: TimetableRecord,
    ) -> tuple[
        int,
        int,
        str,
        int,
    ]:
        """
        Build time-related ML features.

        Uses departure when available,
        otherwise arrival.
        """

        time_value = (
            record.departure
            if record.departure is not None
            else record.arrival
        )

        if time_value is None:
            hour = 0
            minute = 0

        else:
            parts = str(
                time_value
            ).split(":")

            hour = int(parts[0])
            minute = int(parts[1])

        # Match the project's passenger dataset
        # time-period definitions.
        if 6 <= hour <= 9:
            time_period = "Morning peak"
            is_peak = 1

        elif 10 <= hour <= 15:
            time_period = "Daytime"
            is_peak = 0

        elif 16 <= hour <= 19:
            time_period = "Evening peak"
            is_peak = 1

        else:
            time_period = "Night"
            is_peak = 0

        return (
            hour,
            minute,
            time_period,
            is_peak,
        )

    @staticmethod
    def _get_day_features(
        day: int,
    ) -> tuple[str, str]:
        """
        Day 1 = Monday
        ...
        Day 7 = Sunday.
        """

        days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        index = (
            max(
                1,
                min(
                    7,
                    int(day),
                ),
            )
            - 1
        )

        day_of_week = days[index]

        day_type = (
            "Weekend"
            if day_of_week
            in [
                "Saturday",
                "Sunday",
            ]
            else "Weekday"
        )

        return (
            day_of_week,
            day_type,
        )

    # ========================================================
    # ML PREDICTION
    # ========================================================

    def predict_passenger_impact(
        self,
        record: TimetableRecord,
        delay_minutes: float,
        affected_train_count: int,
    ) -> float:
        """
        Predict passenger-delay minutes for one
        changed timetable record.

        If there is no delay, passenger impact is
        treated as zero because the project's target
        represents passenger delay.
        """

        if delay_minutes <= 0:
            return 0.0

        (
            hour,
            minute,
            time_period,
            is_peak,
        ) = self._get_time_features(
            record
        )

        (
            day_of_week,
            day_type,
        ) = self._get_day_features(
            record.day
        )

        scenario = {
            "station_code": record.station_code,
            "station_category": (
                self._get_station_category(
                    record.station_code
                )
            ),
            "station_daily_passengers": (
                self._get_station_daily_passengers(
                    record.station_code
                )
            ),
            "day_of_week": day_of_week,
            "day_type": day_type,
            "hour": hour,
            "minute": minute,
            "time_period": time_period,
            "is_peak_period": is_peak,
            "train_type": self._get_train_type(
                record
            ),
            "train_priority": self._get_train_priority(
                record
            ),
            "disruption_type": (
                self._get_disruption_type()
            ),
            "disruption_duration_minutes": (
                self._get_disruption_duration()
            ),
            "delay_minutes": float(
                delay_minutes
            ),
            "affected_train_count": int(
                affected_train_count
            ),
        }

        df = pd.DataFrame(
            [scenario]
        )

        features = df[
            FEATURE_COLUMNS
        ]

        prediction = self.model.predict(
            features
        )[0]

        return max(
            0.0,
            float(prediction),
        )

    # ========================================================
    # OBJECTIVE
    # ========================================================

    @staticmethod
    def _normalize(
        value: float,
        reference: float,
    ) -> float:
        """
        Normalize a value against a COMMON
        disruption-level reference.
        """

        if reference <= 0:
            return 0.0

        return (
            float(value)
            / float(reference)
        )

    def calculate_objective(
        self,
        total_delay_minutes: float,
        passenger_impact_minutes: float,
    ) -> float:
        """
        Calculate the weighted normalized objective.

        The references are fixed when the evaluator is
        created, so different candidates for the same
        disruption remain directly comparable.
        """

        normalized_delay = (
            self._normalize(
                total_delay_minutes,
                self.delay_reference,
            )
        )

        normalized_passenger_impact = (
            self._normalize(
                passenger_impact_minutes,
                self.passenger_reference,
            )
        )

        total_weight = (
            self.delay_weight
            + self.passenger_weight
        )

        return (
            (
                self.delay_weight
                * normalized_delay
            )
            + (
                self.passenger_weight
                * normalized_passenger_impact
            )
        ) / total_weight

    # ========================================================
    # FEASIBILITY
    # ========================================================

    def check_feasibility(
        self,
        solution: ALNSSolution,
    ) -> tuple[
        bool,
        dict[int, list[str]],
    ]:
        """
        Check the complete candidate using the
        existing FeasibilityChecker.

        The evaluator does not implement a second
        feasibility system.
        """

        from .alns_feasibility import (
            FeasibilityChecker,
        )

        checker = FeasibilityChecker(
            self.db_path,
            disruption=self.disruption,
        )

        return checker.check_solution(
            solution
        )

    # ========================================================
    # COMPLETE EVALUATION
    # ========================================================

    def evaluate(
        self,
        solution: ALNSSolution,
        affected_train_count: int | None = None,
    ) -> ALNSSolution:
        """
        Evaluate one COMPLETE ALNS candidate.

        Steps:
        1. Find changed records.
        2. Calculate total train delay.
        3. Estimate passenger impact.
        4. Check complete-solution feasibility.
        5. Calculate objective.
        6. Store results in ALNSSolution.
        """

        changed_records = (
            self.get_changed_records(
                solution
            )
        )

        total_delay = (
            self.calculate_total_delay(
                changed_records
            )
        )

        if affected_train_count is None:

            affected_train_numbers = {
                record.train_number
                for record in changed_records
            }

            affected_train_count = len(
                affected_train_numbers
            )

        affected_train_count = max(
            1,
            int(affected_train_count),
        )

        passenger_impact = 0.0

        for record in changed_records:

            record_delay = (
                self.calculate_record_delay(
                    record
                )
            )

            passenger_impact += (
                self.predict_passenger_impact(
                    record,
                    record_delay,
                    affected_train_count,
                )
            )

        is_feasible, violations = (
            self.check_feasibility(
                solution
            )
        )

        if is_feasible:
            objective = (
                self.calculate_objective(
                    total_delay,
                    passenger_impact,
                )
            )

        else:
            # Infeasible candidates must never
            # compete with feasible candidates.
            objective = float("inf")

        solution.total_delay_minutes = (
            total_delay
        )

        solution.passenger_impact_minutes = (
            passenger_impact
        )

        solution.objective_value = (
            objective
        )

        solution.is_feasible = (
            is_feasible
        )

        return solution

    # ========================================================
    # DEBUG / EXPLANATION
    # ========================================================

    def get_evaluation_summary(
        self,
        solution: ALNSSolution,
    ) -> dict[str, object]:
        """
        Return a simple summary useful for testing
        and debugging.
        """

        return {
            "record_count": (
                solution.record_count()
            ),
            "changed_record_count": len(
                self.get_changed_records(
                    solution
                )
            ),
            "total_delay_minutes": (
                solution.total_delay_minutes
            ),
            "passenger_impact_minutes": (
                solution.passenger_impact_minutes
            ),
            "objective_value": (
                solution.objective_value
            ),
            "is_feasible": (
                solution.is_feasible
            ),
            "delay_reference": (
                self.delay_reference
            ),
            "passenger_reference": (
                self.passenger_reference
            ),
        }