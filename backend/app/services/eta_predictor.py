"""ETA prediction service using XGBoost regression.

Predicts remaining transit hours for shipments based on geographic,
temporal, weather, and historical features.  Falls back to a simple
historical-average heuristic when the model is unavailable.

Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
"""

import math
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
import xgboost as xgb

from app.models import Coordinates, ETAPrediction, Shipment
from app.services.disruption_detector import _haversine_km  # reuse shared helper

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MODEL_VERSION = "xgb-v1.0-synthetic"

# Average speeds used to derive historical_avg_hours when no external
# data source is available.  ~40 km/h blended average (sea ~30, air ~800).
_AVG_SPEED_KMH = 40.0

# Number of synthetic training samples generated at startup.
_SYNTHETIC_SAMPLES = 500

# Weather condition labels (must match one-hot column order).
_WEATHER_LABELS = ["clear", "rain", "storm", "severe"]


# ---------------------------------------------------------------------------
# ETAPredictor
# ---------------------------------------------------------------------------


class ETAPredictor:
    """Predict remaining transit time for a shipment using XGBoost.

    At initialisation the predictor attempts to load a pre-trained model
    from *model_path*.  If the file does not exist it generates synthetic
    training data and fits a new model, saving it to *model_path* for
    subsequent runs.

    The ``predict`` method extracts features from a ``Shipment`` and
    returns an ``ETAPrediction`` with a confidence interval derived from
    the residual standard deviation observed during training.
    """

    def __init__(self, model_path: str = "models/eta_model.json") -> None:
        self._model_path = model_path
        self._model: Optional[xgb.XGBRegressor] = None
        self._residual_std: float = 0.0
        self._model_available: bool = False

        # Try loading an existing model; fall back to synthetic training.
        if os.path.exists(model_path):
            try:
                self._model = xgb.XGBRegressor()
                self._model.load_model(model_path)
                self._model_available = True
                # Compute residual std from synthetic data for confidence intervals
                self._compute_residual_std()
            except Exception:
                self._model = None
                self._model_available = False

        if not self._model_available:
            self._train_on_synthetic_data()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(self, shipment: Shipment) -> ETAPrediction:
        """Return an ETA prediction with confidence interval.

        Falls back to ``historical_avg_hours ± 20%`` when the model is
        not available.
        """
        features = self.extract_features(shipment)
        now = datetime.now(timezone.utc)

        if self._model_available and self._model is not None:
            X = np.array(features).reshape(1, -1)
            predicted_hours: float = float(self._model.predict(X)[0])
            # Clamp to non-negative
            predicted_hours = max(predicted_hours, 0.0)

            low_hours = max(predicted_hours - self._residual_std, 0.0)
            high_hours = predicted_hours + self._residual_std
        else:
            # Fallback: use historical average ± 20 %
            hist_avg = features[-1]  # last feature is historical_avg_hours
            predicted_hours = max(hist_avg, 0.0)
            low_hours = max(predicted_hours * 0.8, 0.0)
            high_hours = predicted_hours * 1.2

        predicted_arrival = now + timedelta(hours=predicted_hours)
        confidence_low = now + timedelta(hours=low_hours)
        confidence_high = now + timedelta(hours=high_hours)

        # Guarantee ordering: low <= predicted <= high
        if confidence_low > predicted_arrival:
            confidence_low = predicted_arrival
        if confidence_high < predicted_arrival:
            confidence_high = predicted_arrival

        return ETAPrediction(
            shipment_id=shipment.id,
            predicted_arrival=predicted_arrival,
            confidence_low=confidence_low,
            confidence_high=confidence_high,
            model_version=_MODEL_VERSION,
        )

    def extract_features(self, shipment: Shipment) -> list[float]:
        """Extract the feature vector from a shipment.

        Returns a list of 16 floats:
            0  origin_lat
            1  origin_lng
            2  dest_lat
            3  dest_lng
            4  current_lat
            5  current_lng
            6  distance_remaining_km
            7  distance_completed_pct
            8  weather_clear   (one-hot)
            9  weather_rain    (one-hot)
           10  weather_storm   (one-hot)
           11  weather_severe  (one-hot)
           12  hour_sin
           13  hour_cos
           14  day_sin
           15  day_cos
           16  current_delay_minutes
           17  historical_avg_hours
        """
        origin = shipment.origin_coords
        dest = shipment.destination_coords
        current = shipment.current_coords

        total_dist = _haversine_km(origin, dest)
        remaining_dist = _haversine_km(current, dest)

        if total_dist > 0:
            completed_pct = max(0.0, min(1.0, 1.0 - remaining_dist / total_dist))
        else:
            completed_pct = 1.0

        # One-hot weather encoding
        weather = shipment.weather_condition.lower()
        weather_encoded = [1.0 if w == weather else 0.0 for w in _WEATHER_LABELS]

        # Cyclical time encoding
        now = datetime.now(timezone.utc)
        hour = now.hour + now.minute / 60.0
        hour_sin = math.sin(2 * math.pi * hour / 24.0)
        hour_cos = math.cos(2 * math.pi * hour / 24.0)

        day = now.weekday()  # 0=Monday … 6=Sunday
        day_sin = math.sin(2 * math.pi * day / 7.0)
        day_cos = math.cos(2 * math.pi * day / 7.0)

        # Historical average: total_distance / average_speed
        historical_avg = total_dist / _AVG_SPEED_KMH if _AVG_SPEED_KMH > 0 else 0.0

        return [
            origin.lat,
            origin.lng,
            dest.lat,
            dest.lng,
            current.lat,
            current.lng,
            remaining_dist,
            completed_pct,
            *weather_encoded,
            hour_sin,
            hour_cos,
            day_sin,
            day_cos,
            float(shipment.delay_minutes),
            historical_avg,
        ]

    # ------------------------------------------------------------------
    # Training helpers
    # ------------------------------------------------------------------

    def _generate_synthetic_data(self) -> tuple[np.ndarray, np.ndarray]:
        """Generate synthetic shipment feature vectors and target values.

        Returns (X, y) where X has shape (n, 18) and y has shape (n,).
        """
        rng = np.random.RandomState(42)

        n = _SYNTHETIC_SAMPLES

        # Random coordinates (lat/lng)
        origin_lat = rng.uniform(-60, 60, n)
        origin_lng = rng.uniform(-170, 170, n)
        dest_lat = rng.uniform(-60, 60, n)
        dest_lng = rng.uniform(-170, 170, n)

        # Completed fraction
        completed_pct = rng.uniform(0.0, 1.0, n)

        # Compute total and remaining distances via vectorised haversine
        total_dist = np.array(
            [
                _haversine_km(
                    Coordinates(lat=float(origin_lat[i]), lng=float(origin_lng[i])),
                    Coordinates(lat=float(dest_lat[i]), lng=float(dest_lng[i])),
                )
                for i in range(n)
            ]
        )
        remaining_dist = total_dist * (1.0 - completed_pct)

        # Current position: linear interpolation + noise
        current_lat = origin_lat + (dest_lat - origin_lat) * completed_pct + rng.normal(0, 0.5, n)
        current_lng = origin_lng + (dest_lng - origin_lng) * completed_pct + rng.normal(0, 0.5, n)

        # Weather one-hot (random category per sample)
        weather_idx = rng.randint(0, 4, n)
        weather_onehot = np.zeros((n, 4))
        weather_onehot[np.arange(n), weather_idx] = 1.0

        # Cyclical time features
        hours = rng.uniform(0, 24, n)
        hour_sin = np.sin(2 * np.pi * hours / 24.0)
        hour_cos = np.cos(2 * np.pi * hours / 24.0)

        days = rng.randint(0, 7, n).astype(float)
        day_sin = np.sin(2 * np.pi * days / 7.0)
        day_cos = np.cos(2 * np.pi * days / 7.0)

        # Delay and historical average
        delay_minutes = rng.exponential(30, n)
        historical_avg = total_dist / _AVG_SPEED_KMH

        # Assemble feature matrix (18 columns)
        X = np.column_stack(
            [
                origin_lat,
                origin_lng,
                dest_lat,
                dest_lng,
                current_lat,
                current_lng,
                remaining_dist,
                completed_pct,
                weather_onehot,
                hour_sin,
                hour_cos,
                day_sin,
                day_cos,
                delay_minutes,
                historical_avg,
            ]
        )

        # Target: remaining transit hours
        # Base: remaining_dist / speed, with weather & delay adjustments
        weather_factor = 1.0 + 0.1 * weather_idx  # 1.0 – 1.3
        y = (remaining_dist / _AVG_SPEED_KMH) * weather_factor + delay_minutes / 60.0
        # Add realistic noise
        y += rng.normal(0, y * 0.05 + 0.5)
        y = np.maximum(y, 0.0)

        return X, y

    def _compute_residual_std(self) -> None:
        """Compute residual standard deviation using synthetic data.

        Called when a model is loaded from file and needs a residual_std
        for confidence interval calculation.
        """
        if self._model is None:
            return
        X, y = self._generate_synthetic_data()
        y_pred = self._model.predict(X)
        residuals = y - y_pred
        self._residual_std = float(np.std(residuals))

    def _train_on_synthetic_data(self) -> None:
        """Generate synthetic shipment data and fit the XGBoost model."""
        X, y = self._generate_synthetic_data()

        # Fit model
        self._model = xgb.XGBRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            objective="reg:squarederror",
            random_state=42,
        )
        self._model.fit(X, y)

        # Compute residual std for confidence interval
        y_pred = self._model.predict(X)
        residuals = y - y_pred
        self._residual_std = float(np.std(residuals))
        self._model_available = True

        # Persist model for future runs
        try:
            os.makedirs(os.path.dirname(self._model_path) or ".", exist_ok=True)
            self._model.save_model(self._model_path)
        except Exception:
            pass  # non-critical; model is still in memory
