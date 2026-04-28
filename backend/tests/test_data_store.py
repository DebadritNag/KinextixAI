"""Unit tests for the DataStore singleton."""

import threading
from datetime import datetime, timezone

from app.models import (
    AnalyticsData,
    Coordinates,
    OptimizationWeights,
    RiskAlert,
    Settings,
    Severity,
    Shipment,
    ShipmentStatus,
)
from app.services.data_store import DataStore


def _make_shipment(shipment_id: str = "SHP-001", status: ShipmentStatus = ShipmentStatus.IN_TRANSIT) -> Shipment:
    """Helper to create a test shipment."""
    now = datetime.now(timezone.utc)
    return Shipment(
        id=shipment_id,
        origin="Shanghai",
        destination="Los Angeles",
        origin_coords=Coordinates(lat=31.23, lng=121.47),
        destination_coords=Coordinates(lat=33.94, lng=-118.41),
        current_coords=Coordinates(lat=32.0, lng=-110.0),
        status=status,
        created_at=now,
        updated_at=now,
    )


def _make_alert(alert_id: str = "ALT-001", severity: Severity = Severity.HIGH) -> RiskAlert:
    """Helper to create a test alert."""
    return RiskAlert(
        id=alert_id,
        shipment_id="SHP-001",
        severity=severity,
        title="Test Alert",
        description="Test description",
        created_at=datetime.now(timezone.utc),
    )


class TestDataStoreShipments:
    """Tests for shipment CRUD operations."""

    def test_get_shipments_empty(self) -> None:
        store = DataStore()
        assert store.get_shipments() == []

    def test_upsert_and_get_shipment(self) -> None:
        store = DataStore()
        shipment = _make_shipment("SHP-001")
        store.upsert_shipment(shipment)

        result = store.get_shipment("SHP-001")
        assert result is not None
        assert result.id == "SHP-001"
        assert result.origin == "Shanghai"

    def test_get_shipment_not_found(self) -> None:
        store = DataStore()
        assert store.get_shipment("NONEXISTENT") is None

    def test_upsert_overwrites_existing(self) -> None:
        store = DataStore()
        store.upsert_shipment(_make_shipment("SHP-001", ShipmentStatus.IN_TRANSIT))
        store.upsert_shipment(_make_shipment("SHP-001", ShipmentStatus.DELAYED))

        result = store.get_shipment("SHP-001")
        assert result is not None
        assert result.status == ShipmentStatus.DELAYED

    def test_get_shipments_returns_all(self) -> None:
        store = DataStore()
        store.upsert_shipment(_make_shipment("SHP-001"))
        store.upsert_shipment(_make_shipment("SHP-002"))
        store.upsert_shipment(_make_shipment("SHP-003"))

        shipments = store.get_shipments()
        assert len(shipments) == 3

    def test_get_active_shipment_count(self) -> None:
        store = DataStore()
        store.upsert_shipment(_make_shipment("SHP-001", ShipmentStatus.IN_TRANSIT))
        store.upsert_shipment(_make_shipment("SHP-002", ShipmentStatus.DELIVERED))
        store.upsert_shipment(_make_shipment("SHP-003", ShipmentStatus.DELAYED))

        assert store.get_active_shipment_count() == 2


class TestDataStoreAlerts:
    """Tests for alert operations."""

    def test_get_alerts_empty(self) -> None:
        store = DataStore()
        assert store.get_alerts() == []

    def test_add_and_get_alerts(self) -> None:
        store = DataStore()
        store.add_alert(_make_alert("ALT-001", Severity.HIGH))
        store.add_alert(_make_alert("ALT-002", Severity.LOW))

        alerts = store.get_alerts()
        assert len(alerts) == 2

    def test_get_alerts_filter_by_severity(self) -> None:
        store = DataStore()
        store.add_alert(_make_alert("ALT-001", Severity.HIGH))
        store.add_alert(_make_alert("ALT-002", Severity.LOW))
        store.add_alert(_make_alert("ALT-003", Severity.HIGH))

        high_alerts = store.get_alerts(severity="high")
        assert len(high_alerts) == 2
        assert all(a.severity == Severity.HIGH for a in high_alerts)

    def test_get_alerts_filter_no_match(self) -> None:
        store = DataStore()
        store.add_alert(_make_alert("ALT-001", Severity.HIGH))

        low_alerts = store.get_alerts(severity="low")
        assert len(low_alerts) == 0

    def test_clear_alerts(self) -> None:
        store = DataStore()
        store.add_alert(_make_alert("ALT-001"))
        store.add_alert(_make_alert("ALT-002"))
        assert len(store.get_alerts()) == 2

        store.clear_alerts()
        assert len(store.get_alerts()) == 0


class TestDataStoreSettings:
    """Tests for settings operations."""

    def test_default_settings(self) -> None:
        store = DataStore()
        settings = store.get_settings()

        assert settings.sla_thresholds == {"standard": 72.0, "express": 24.0, "overnight": 12.0}
        assert settings.penalties == {"standard": 50.0, "express": 150.0, "overnight": 300.0}
        assert settings.default_weights.cost == 0.25
        assert settings.default_weights.time == 0.25
        assert settings.default_weights.carbon == 0.25
        assert settings.default_weights.risk == 0.25

    def test_update_settings(self) -> None:
        store = DataStore()
        new_settings = Settings(
            sla_thresholds={"standard": 48.0, "express": 12.0, "overnight": 6.0},
            penalties={"standard": 100.0, "express": 300.0, "overnight": 600.0},
            default_weights=OptimizationWeights(cost=0.5, time=0.2, carbon=0.2, risk=0.1),
        )
        store.update_settings(new_settings)

        result = store.get_settings()
        assert result.sla_thresholds["standard"] == 48.0
        assert result.penalties["express"] == 300.0
        assert result.default_weights.cost == 0.5


class TestDataStoreAnalytics:
    """Tests for analytics operations."""

    def test_get_analytics_empty(self) -> None:
        store = DataStore()
        analytics = store.get_analytics("24h")

        assert isinstance(analytics, AnalyticsData)
        assert analytics.delay_trends == []
        assert analytics.cost_savings == []
        assert analytics.carbon_reduction == []
        assert analytics.sla_compliance_pct == 0.0
        assert analytics.sla_trend == []

    def test_add_and_get_analytics_snapshot(self) -> None:
        store = DataStore()
        now = datetime.now(timezone.utc)
        store.add_analytics_snapshot({
            "timestamp": now,
            "delay_trend": {"date": now.isoformat(), "avg_delay_minutes": 15, "count": 10},
            "cost_saving": {"date": now.isoformat(), "baseline_cost": 1000, "optimized_cost": 800},
            "carbon_reduction": {"date": now.isoformat(), "baseline_carbon": 500, "optimized_carbon": 350},
            "sla_compliance_pct": 92.5,
        })

        analytics = store.get_analytics("24h")
        assert len(analytics.delay_trends) == 1
        assert len(analytics.cost_savings) == 1
        assert len(analytics.carbon_reduction) == 1
        assert analytics.sla_compliance_pct == 92.5
        assert len(analytics.sla_trend) == 1

    def test_analytics_time_range_filtering(self) -> None:
        store = DataStore()
        now = datetime.now(timezone.utc)
        from datetime import timedelta

        # Recent snapshot (within 24h)
        store.add_analytics_snapshot({
            "timestamp": now,
            "sla_compliance_pct": 95.0,
        })
        # Old snapshot (8 days ago, outside 7d range)
        store.add_analytics_snapshot({
            "timestamp": now - timedelta(days=8),
            "sla_compliance_pct": 80.0,
        })

        analytics_24h = store.get_analytics("24h")
        assert analytics_24h.sla_compliance_pct == 95.0

        analytics_7d = store.get_analytics("7d")
        assert analytics_7d.sla_compliance_pct == 95.0  # Only recent one is within 7d

        analytics_30d = store.get_analytics("30d")
        assert analytics_30d.sla_compliance_pct == 87.5  # Average of 95 and 80


class TestDataStoreThreadSafety:
    """Tests for concurrent access safety."""

    def test_concurrent_upsert_shipments(self) -> None:
        store = DataStore()
        errors: list[Exception] = []

        def upsert_batch(start: int, count: int) -> None:
            try:
                for i in range(start, start + count):
                    store.upsert_shipment(_make_shipment(f"SHP-{i:04d}"))
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=upsert_batch, args=(0, 50)),
            threading.Thread(target=upsert_batch, args=(50, 50)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(store.get_shipments()) == 100

    def test_concurrent_add_alerts(self) -> None:
        store = DataStore()
        errors: list[Exception] = []

        def add_batch(start: int, count: int) -> None:
            try:
                for i in range(start, start + count):
                    store.add_alert(_make_alert(f"ALT-{i:04d}"))
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=add_batch, args=(0, 50)),
            threading.Thread(target=add_batch, args=(50, 50)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(store.get_alerts()) == 100


class TestDataStoreSingleton:
    """Tests for module-level singleton behavior."""

    def test_module_singleton_is_datastore(self) -> None:
        from app.services.data_store import data_store
        assert isinstance(data_store, DataStore)
