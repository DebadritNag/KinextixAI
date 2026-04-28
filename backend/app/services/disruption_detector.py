"""Disruption detection service using Isolation Forest anomaly detection.

Analyzes shipment data to identify potential supply chain disruptions by
extracting features (location deviation, time deviation, weather severity,
historical delay frequency) and scoring them with an Isolation Forest model.

Requirements: 10.1, 10.2, 10.3, 10.4, 20.4
"""

import math
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import numpy as np
from sklearn.ensemble import IsolationForest

from app.models import Coordinates, RiskAlert, Severity, Shipment

# Weather condition to numeric severity mapping
_WEATHER_SEVERITY_MAP: dict[str, int] = {
    "clear": 0,
    "rain": 1,
    "storm": 2,
    "severe": 3,
}


def _haversine_km(a: Coordinates, b: Coordinates) -> float:
    """Compute the Haversine distance in kilometres between two coordinates.

    Uses the standard spherical law of cosines approximation with Earth
    radius of 6371 km.
    """
    lat1, lng1 = math.radians(a.lat), math.radians(a.lng)
    lat2, lng2 = math.radians(b.lat), math.radians(b.lng)

    dlat = lat2 - lat1
    dlng = lng2 - lng1

    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    )
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def _expected_position(shipment: Shipment) -> Coordinates:
    """Estimate the expected current position via linear interpolation.

    Uses elapsed time as a fraction of total expected transit time to
    interpolate between origin and destination coordinates.
    """
    now = datetime.now(timezone.utc)
    created = shipment.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)

    # Use ETA if available, otherwise estimate 48h transit
    if shipment.eta_predicted is not None:
        eta = shipment.eta_predicted
        if eta.tzinfo is None:
            eta = eta.replace(tzinfo=timezone.utc)
    else:
        from datetime import timedelta

        eta = created + timedelta(hours=48)

    total_seconds = max((eta - created).total_seconds(), 1.0)
    elapsed_seconds = (now - created).total_seconds()
    fraction = max(0.0, min(1.0, elapsed_seconds / total_seconds))

    interp_lat = shipment.origin_coords.lat + fraction * (
        shipment.destination_coords.lat - shipment.origin_coords.lat
    )
    interp_lng = shipment.origin_coords.lng + fraction * (
        shipment.destination_coords.lng - shipment.origin_coords.lng
    )
    return Coordinates(lat=interp_lat, lng=interp_lng)


class DisruptionDetector:
    """Anomaly-based disruption detector using scikit-learn Isolation Forest.

    The model is pre-fitted on 1000 synthetic "normal" samples at
    initialisation so it can score real shipments immediately.
    """

    def __init__(self, contamination: float = 0.1) -> None:
        """Initialise with an Isolation Forest model.

        Args:
            contamination: Expected proportion of anomalies (default 0.1).
        """
        self._model = IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=42,
            max_features=1.0,
        )
        self._fit_on_synthetic_data()

    # ── Feature extraction ───────────────────────────────────────────

    def extract_features(self, shipment: Shipment) -> list[float]:
        """Extract the four-element feature vector from a shipment.

        Returns:
            [location_deviation, time_deviation, weather_severity,
             historical_delay_freq]
        """
        # 1. location_deviation — haversine km from expected position
        expected = _expected_position(shipment)
        location_deviation = _haversine_km(shipment.current_coords, expected)

        # 2. time_deviation — (actual_elapsed - expected_elapsed) / expected_total
        now = datetime.now(timezone.utc)
        created = shipment.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)

        if shipment.eta_predicted is not None:
            eta = shipment.eta_predicted
            if eta.tzinfo is None:
                eta = eta.replace(tzinfo=timezone.utc)
        else:
            from datetime import timedelta

            eta = created + timedelta(hours=48)

        expected_total = max((eta - created).total_seconds(), 1.0)
        actual_elapsed = (now - created).total_seconds()

        # Expected elapsed is the same as actual elapsed for an on-time shipment;
        # delay_minutes captures the deviation.
        expected_elapsed = actual_elapsed - (shipment.delay_minutes * 60)
        time_deviation = (actual_elapsed - expected_elapsed) / expected_total

        # 3. weather_severity — map string to numeric
        weather_severity = float(
            _WEATHER_SEVERITY_MAP.get(shipment.weather_condition.lower(), 0)
        )

        # 4. historical_delay_freq — heuristic based on current delay
        historical_delay_freq = min(1.0, shipment.delay_minutes / 120.0) if shipment.delay_minutes > 0 else 0.0

        return [location_deviation, time_deviation, weather_severity, historical_delay_freq]

    # ── Analysis ─────────────────────────────────────────────────────

    def analyze(self, shipment: Shipment) -> Optional[RiskAlert]:
        """Analyse a single shipment for anomalies.

        Returns a RiskAlert if the shipment is anomalous, None if normal.
        Must complete within 2 seconds.
        """
        features = self.extract_features(shipment)
        feature_array = np.array([features])

        score = float(self._model.score_samples(feature_array)[0])

        if score >= 0:
            return None

        severity = self._classify_severity(score)
        return self._build_alert(shipment, severity, score)

    def analyze_batch(self, shipments: list[Shipment]) -> list[RiskAlert]:
        """Analyse multiple shipments and return alerts for anomalous ones."""
        if not shipments:
            return []

        feature_matrix = np.array(
            [self.extract_features(s) for s in shipments]
        )
        scores = self._model.score_samples(feature_matrix)

        alerts: list[RiskAlert] = []
        for shipment, score in zip(shipments, scores):
            score_val = float(score)
            if score_val < 0:
                severity = self._classify_severity(score_val)
                alerts.append(self._build_alert(shipment, severity, score_val))

        return alerts

    # ── Internal helpers ─────────────────────────────────────────────

    @staticmethod
    def _classify_severity(score: float) -> Severity:
        """Map an anomaly score to a severity level.

        score < -0.3        → HIGH
        -0.3 <= score < -0.15 → MEDIUM
        -0.15 <= score < 0    → LOW
        """
        if score < -0.3:
            return Severity.HIGH
        if score < -0.15:
            return Severity.MEDIUM
        return Severity.LOW

    @staticmethod
    def _build_alert(
        shipment: Shipment, severity: Severity, score: float
    ) -> RiskAlert:
        """Construct a RiskAlert from analysis results."""
        severity_label = severity.value.upper()
        return RiskAlert(
            id=str(uuid4()),
            shipment_id=shipment.id,
            severity=severity,
            title=f"{severity_label} disruption risk detected",
            description=(
                f"Shipment {shipment.id} from {shipment.origin} to "
                f"{shipment.destination} shows anomalous behaviour "
                f"(score={score:.3f}). Weather: {shipment.weather_condition}, "
                f"delay: {shipment.delay_minutes}min."
            ),
            created_at=datetime.now(timezone.utc),
            is_active=True,
        )

    def _fit_on_synthetic_data(self) -> None:
        """Pre-fit the Isolation Forest on 1000 synthetic normal samples.

        Generates feature vectors representing typical (non-anomalous)
        shipment behaviour:
        - location_deviation: small deviations (0-20 km)
        - time_deviation: near zero (-0.05 to 0.1)
        - weather_severity: mostly clear/rain (0-1)
        - historical_delay_freq: low (0-0.15)
        """
        rng = np.random.RandomState(42)
        n_samples = 1000

        location_deviation = rng.exponential(scale=5.0, size=n_samples)
        location_deviation = np.clip(location_deviation, 0, 20)

        time_deviation = rng.normal(loc=0.02, scale=0.03, size=n_samples)
        time_deviation = np.clip(time_deviation, -0.05, 0.1)

        weather_severity = rng.choice([0, 0, 0, 0, 1, 1], size=n_samples).astype(float)

        historical_delay_freq = rng.beta(a=1.5, b=15, size=n_samples)
        historical_delay_freq = np.clip(historical_delay_freq, 0, 0.15)

        training_data = np.column_stack(
            [location_deviation, time_deviation, weather_severity, historical_delay_freq]
        )
        self._model.fit(training_data)
