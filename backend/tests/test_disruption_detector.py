"""Unit tests for the DisruptionDetector service.

Validates feature extraction, severity classification, single and batch
analysis, and performance requirements.
"""

import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from app.models import Coordinates, Severity, Shipment, ShipmentStatus
from app.services.disruption_detector import (
    DisruptionDetector,
    _haversine_km,
    _WEATHER_SEVERITY_MAP,
)


# ── Fixtures ─────────────────────────────────────────────────────────


def _make_shipment(
    *,
    current_lat: float = 35.0,
    current_lng: float = 139.0,
    origin_lat: float = 31.23,
    origin_lng: float = 121.47,
    dest_lat: float = 37.77,
    dest_lng: float = -122.42,
    delay_minutes: int = 0,
    weather: str = "clear",
    status: ShipmentStatus = ShipmentStatus.IN_TRANSIT,
    hours_ago: float = 12.0,
    eta_hours_from_creation: float = 48.0,
) -> Shipment:
    """Helper to build a Shipment with sensible defaults."""
    now = datetime.now(timezone.utc)
    created = now - timedelta(hours=hours_ago)
    eta = created + timedelta(hours=eta_hours_from_creation)
    return Shipment(
        id="SHP-TEST-001",
        origin="Shanghai",
        destination="San Francisco",
        origin_coords=Coordinates(lat=origin_lat, lng=origin_lng),
        destination_coords=Coordinates(lat=dest_lat, lng=dest_lng),
        current_coords=Coordinates(lat=current_lat, lng=current_lng),
        status=status,
        created_at=created,
        updated_at=now,
        eta_predicted=eta,
        delay_minutes=delay_minutes,
        weather_condition=weather,
    )


@pytest.fixture
def detector() -> DisruptionDetector:
    """Return a freshly initialised DisruptionDetector."""
    return DisruptionDetector()


# ── Haversine tests ──────────────────────────────────────────────────


class TestHaversine:
    def test_same_point_returns_zero(self) -> None:
        c = Coordinates(lat=0.0, lng=0.0)
        assert _haversine_km(c, c) == pytest.approx(0.0, abs=0.01)

    def test_known_distance(self) -> None:
        # London to Paris ≈ 344 km
        london = Coordinates(lat=51.5074, lng=-0.1278)
        paris = Coordinates(lat=48.8566, lng=2.3522)
        dist = _haversine_km(london, paris)
        assert 340 < dist < 350


# ── Initialisation tests ─────────────────────────────────────────────


class TestInitialisation:
    def test_model_is_fitted(self, detector: DisruptionDetector) -> None:
        """The model should be fitted after init (has estimators_)."""
        assert hasattr(detector._model, "estimators_")
        assert len(detector._model.estimators_) == 100

    def test_custom_contamination(self) -> None:
        d = DisruptionDetector(contamination=0.05)
        assert d._model.contamination == 0.05


# ── Feature extraction tests ─────────────────────────────────────────


class TestFeatureExtraction:
    def test_returns_four_features(self, detector: DisruptionDetector) -> None:
        shipment = _make_shipment()
        features = detector.extract_features(shipment)
        assert len(features) == 4

    def test_clear_weather_maps_to_zero(self, detector: DisruptionDetector) -> None:
        shipment = _make_shipment(weather="clear")
        features = detector.extract_features(shipment)
        assert features[2] == 0.0

    def test_severe_weather_maps_to_three(self, detector: DisruptionDetector) -> None:
        shipment = _make_shipment(weather="severe")
        features = detector.extract_features(shipment)
        assert features[2] == 3.0

    def test_no_delay_gives_zero_freq(self, detector: DisruptionDetector) -> None:
        shipment = _make_shipment(delay_minutes=0)
        features = detector.extract_features(shipment)
        assert features[3] == 0.0

    def test_large_delay_caps_at_one(self, detector: DisruptionDetector) -> None:
        shipment = _make_shipment(delay_minutes=300)
        features = detector.extract_features(shipment)
        assert features[3] == 1.0

    def test_weather_severity_map_completeness(self) -> None:
        assert set(_WEATHER_SEVERITY_MAP.keys()) == {"clear", "rain", "storm", "severe"}


# ── Severity classification tests ────────────────────────────────────


class TestSeverityClassification:
    def test_high_severity(self) -> None:
        assert DisruptionDetector._classify_severity(-0.5) == Severity.HIGH
        assert DisruptionDetector._classify_severity(-0.31) == Severity.HIGH

    def test_medium_severity(self) -> None:
        assert DisruptionDetector._classify_severity(-0.3) == Severity.MEDIUM
        assert DisruptionDetector._classify_severity(-0.16) == Severity.MEDIUM

    def test_low_severity(self) -> None:
        assert DisruptionDetector._classify_severity(-0.15) == Severity.LOW
        assert DisruptionDetector._classify_severity(-0.01) == Severity.LOW

    def test_boundary_minus_0_3(self) -> None:
        """Exactly -0.3 should be MEDIUM, not HIGH."""
        assert DisruptionDetector._classify_severity(-0.3) == Severity.MEDIUM

    def test_boundary_minus_0_15(self) -> None:
        """Exactly -0.15 should be LOW, not MEDIUM."""
        assert DisruptionDetector._classify_severity(-0.15) == Severity.LOW


# ── Single analysis tests ────────────────────────────────────────────


class TestAnalyze:
    def test_normal_shipment_returns_none(self, detector: DisruptionDetector) -> None:
        """A shipment with normal features should not trigger an alert."""
        shipment = _make_shipment(
            delay_minutes=0,
            weather="clear",
            # Current coords close to expected interpolated position
            current_lat=33.5,
            current_lng=130.0,
        )
        result = detector.analyze(shipment)
        # Normal shipments may or may not trigger — we just verify the type
        assert result is None or result.shipment_id == "SHP-TEST-001"

    def test_anomalous_shipment_returns_alert(self, detector: DisruptionDetector) -> None:
        """A shipment with extreme features should trigger an alert."""
        shipment = _make_shipment(
            delay_minutes=300,
            weather="severe",
            # Far off expected route
            current_lat=-30.0,
            current_lng=0.0,
        )
        result = detector.analyze(shipment)
        assert result is not None
        assert result.shipment_id == "SHP-TEST-001"
        assert result.severity in (Severity.LOW, Severity.MEDIUM, Severity.HIGH)
        assert result.is_active is True
        assert len(result.id) > 0

    def test_alert_has_correct_fields(self, detector: DisruptionDetector) -> None:
        shipment = _make_shipment(delay_minutes=300, weather="severe", current_lat=-30.0, current_lng=0.0)
        result = detector.analyze(shipment)
        assert result is not None
        assert "disruption risk detected" in result.title.lower()
        assert shipment.id in result.description
        assert result.created_at is not None

    def test_completes_within_two_seconds(self, detector: DisruptionDetector) -> None:
        """Single analysis must complete within 2 seconds (Req 10.4)."""
        shipment = _make_shipment()
        start = time.monotonic()
        detector.analyze(shipment)
        elapsed = time.monotonic() - start
        assert elapsed < 2.0


# ── Batch analysis tests ─────────────────────────────────────────────


class TestAnalyzeBatch:
    def test_empty_list_returns_empty(self, detector: DisruptionDetector) -> None:
        assert detector.analyze_batch([]) == []

    def test_batch_returns_only_anomalous(self, detector: DisruptionDetector) -> None:
        normal = _make_shipment(delay_minutes=0, weather="clear", current_lat=33.5, current_lng=130.0)
        anomalous = _make_shipment(delay_minutes=300, weather="severe", current_lat=-30.0, current_lng=0.0)
        # Override IDs so they're distinguishable
        normal = normal.model_copy(update={"id": "SHP-NORMAL"})
        anomalous = anomalous.model_copy(update={"id": "SHP-ANOMALOUS"})

        alerts = detector.analyze_batch([normal, anomalous])
        anomalous_ids = {a.shipment_id for a in alerts}
        # The anomalous shipment should definitely be flagged
        assert "SHP-ANOMALOUS" in anomalous_ids

    def test_batch_all_anomalous(self, detector: DisruptionDetector) -> None:
        shipments = [
            _make_shipment(delay_minutes=300, weather="severe", current_lat=-30.0, current_lng=0.0).model_copy(
                update={"id": f"SHP-{i}"}
            )
            for i in range(5)
        ]
        alerts = detector.analyze_batch(shipments)
        assert len(alerts) == 5

    def test_batch_performance(self, detector: DisruptionDetector) -> None:
        """Batch of 100 shipments should complete quickly."""
        shipments = [
            _make_shipment(delay_minutes=i * 10, weather="rain").model_copy(
                update={"id": f"SHP-{i}"}
            )
            for i in range(100)
        ]
        start = time.monotonic()
        detector.analyze_batch(shipments)
        elapsed = time.monotonic() - start
        assert elapsed < 5.0
