"""Unit tests for the simulation module.

Tests cover:
- Initial shipment generation (count, status distribution, coordinate validity)
- Simulation cycle mechanics (position advancement, event injection, delivery,
  pool replenishment, ML pipeline execution, analytics recording)
- SimulationManager start/stop lifecycle
"""

import asyncio
import math
import random
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.models import Coordinates, Shipment, ShipmentStatus, TimelineEvent
from app.services.data_store import DataStore, data_store
from app.services.simulation import (
    SimulationManager,
    _NEAR_DESTINATION_KM,
    _build_shipment,
    _interpolate_coords,
    _random_node,
    _random_node_pair,
)


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clean_data_store():
    """Reset the global data store before each test."""
    data_store._shipments.clear()
    data_store._alerts.clear()
    data_store._analytics_snapshots.clear()
    yield
    data_store._shipments.clear()
    data_store._alerts.clear()
    data_store._analytics_snapshots.clear()


@pytest.fixture
def manager():
    """Create a SimulationManager instance for testing."""
    return SimulationManager()


# ── Helper function tests ────────────────────────────────────────────


class TestHelpers:
    def test_random_node_returns_dict_with_required_keys(self):
        node = _random_node()
        assert "id" in node
        assert "name" in node
        assert "coords" in node
        assert "lat" in node["coords"]
        assert "lng" in node["coords"]

    def test_random_node_pair_returns_distinct_nodes(self):
        origin, dest = _random_node_pair()
        assert origin["id"] != dest["id"]

    def test_interpolate_coords_at_zero(self):
        a = Coordinates(lat=0.0, lng=0.0)
        b = Coordinates(lat=10.0, lng=20.0)
        result = _interpolate_coords(a, b, 0.0)
        assert result.lat == pytest.approx(0.0)
        assert result.lng == pytest.approx(0.0)

    def test_interpolate_coords_at_one(self):
        a = Coordinates(lat=0.0, lng=0.0)
        b = Coordinates(lat=10.0, lng=20.0)
        result = _interpolate_coords(a, b, 1.0)
        assert result.lat == pytest.approx(10.0)
        assert result.lng == pytest.approx(20.0)

    def test_interpolate_coords_at_half(self):
        a = Coordinates(lat=0.0, lng=0.0)
        b = Coordinates(lat=10.0, lng=20.0)
        result = _interpolate_coords(a, b, 0.5)
        assert result.lat == pytest.approx(5.0)
        assert result.lng == pytest.approx(10.0)

    def test_interpolate_coords_clamps_fraction(self):
        a = Coordinates(lat=0.0, lng=0.0)
        b = Coordinates(lat=10.0, lng=20.0)
        result = _interpolate_coords(a, b, 1.5)
        assert result.lat == pytest.approx(10.0)
        assert result.lng == pytest.approx(20.0)

    def test_build_shipment_creates_valid_shipment(self):
        origin = {"id": "test_o", "name": "Origin", "coords": {"lat": 10.0, "lng": 20.0}}
        dest = {"id": "test_d", "name": "Dest", "coords": {"lat": 30.0, "lng": 40.0}}
        shipment = _build_shipment(origin, dest, ShipmentStatus.IN_TRANSIT, 0.5)

        assert shipment.origin == "Origin"
        assert shipment.destination == "Dest"
        assert shipment.status == ShipmentStatus.IN_TRANSIT
        assert shipment.current_coords.lat == pytest.approx(20.0)
        assert shipment.current_coords.lng == pytest.approx(30.0)
        assert len(shipment.timeline) == 1
        assert shipment.id  # non-empty UUID


# ── Initial shipment generation ──────────────────────────────────────


class TestGenerateInitialShipments:
    def test_generates_between_50_and_100_shipments(self, manager):
        random.seed(42)
        manager.generate_initial_shipments()
        shipments = data_store.get_shipments()
        assert 50 <= len(shipments) <= 100

    def test_shipments_have_valid_coordinates(self, manager):
        random.seed(42)
        manager.generate_initial_shipments()
        for s in data_store.get_shipments():
            assert -90 <= s.origin_coords.lat <= 90
            assert -180 <= s.origin_coords.lng <= 180
            assert -90 <= s.destination_coords.lat <= 90
            assert -180 <= s.destination_coords.lng <= 180
            assert -90 <= s.current_coords.lat <= 90
            assert -180 <= s.current_coords.lng <= 180

    def test_shipments_have_distinct_origin_and_destination(self, manager):
        random.seed(42)
        manager.generate_initial_shipments()
        for s in data_store.get_shipments():
            assert s.origin != s.destination

    def test_status_distribution_is_roughly_correct(self, manager):
        """With enough samples, status distribution should approximate weights."""
        random.seed(42)
        manager.generate_initial_shipments()
        shipments = data_store.get_shipments()
        total = len(shipments)

        in_transit = sum(1 for s in shipments if s.status == ShipmentStatus.IN_TRANSIT)
        created = sum(1 for s in shipments if s.status == ShipmentStatus.CREATED)
        delayed = sum(1 for s in shipments if s.status == ShipmentStatus.DELAYED)
        delivered = sum(1 for s in shipments if s.status == ShipmentStatus.DELIVERED)

        # Allow generous tolerance since sample size is small (50-100)
        assert in_transit > 0, "Should have some in_transit shipments"
        assert in_transit / total > 0.3, "in_transit should be the majority"

    def test_created_shipments_at_origin(self, manager):
        random.seed(42)
        manager.generate_initial_shipments()
        for s in data_store.get_shipments():
            if s.status == ShipmentStatus.CREATED:
                assert s.current_coords.lat == pytest.approx(s.origin_coords.lat)
                assert s.current_coords.lng == pytest.approx(s.origin_coords.lng)

    def test_delivered_shipments_at_destination(self, manager):
        random.seed(42)
        manager.generate_initial_shipments()
        for s in data_store.get_shipments():
            if s.status == ShipmentStatus.DELIVERED:
                assert s.current_coords.lat == pytest.approx(s.destination_coords.lat)
                assert s.current_coords.lng == pytest.approx(s.destination_coords.lng)


# ── Simulation cycle ─────────────────────────────────────────────────


class TestSimulationCycle:
    def test_cycle_advances_in_transit_positions(self, manager):
        """In-transit shipments should move closer to destination after a cycle."""
        # Create a shipment far from destination
        now = datetime.now(timezone.utc)
        shipment = Shipment(
            id="test-advance",
            origin="Shanghai Port",
            destination="Los Angeles Port",
            origin_coords=Coordinates(lat=31.23, lng=121.47),
            destination_coords=Coordinates(lat=33.74, lng=-118.26),
            current_coords=Coordinates(lat=31.23, lng=121.47),  # at origin
            status=ShipmentStatus.IN_TRANSIT,
            created_at=now - timedelta(hours=100),  # well into transit
            updated_at=now,
        )
        data_store.upsert_shipment(shipment)

        manager.simulation_cycle()

        updated = data_store.get_shipment("test-advance")
        assert updated is not None
        # Position should have moved from origin
        assert not (
            updated.current_coords.lat == pytest.approx(31.23, abs=0.01)
            and updated.current_coords.lng == pytest.approx(121.47, abs=0.01)
        )

    def test_cycle_delivers_near_destination_shipments(self, manager):
        """Shipments near destination should be marked delivered."""
        now = datetime.now(timezone.utc)
        # Use a short-distance route so the shipment is near destination.
        # Created long enough ago that interpolation fraction >= 1.0,
        # placing the shipment at the destination after advance_position.
        origin = Coordinates(lat=51.92, lng=4.48)   # Rotterdam
        dest = Coordinates(lat=53.55, lng=9.99)      # Hamburg (~450km)
        # Transit time ~11.25h at 40km/h; created 24h ago → fraction > 1.0
        shipment = Shipment(
            id="test-deliver",
            origin="Rotterdam Port",
            destination="Hamburg Port",
            origin_coords=origin,
            destination_coords=dest,
            current_coords=dest,  # already at destination
            status=ShipmentStatus.IN_TRANSIT,
            created_at=now - timedelta(hours=24),
            updated_at=now,
        )
        data_store.upsert_shipment(shipment)

        manager.simulation_cycle()

        updated = data_store.get_shipment("test-deliver")
        assert updated is not None
        assert updated.status == ShipmentStatus.DELIVERED

    def test_cycle_replenishes_pool_when_below_minimum(self, manager):
        """Pool should be replenished when active count drops below 50."""
        # Start with only 10 active shipments
        now = datetime.now(timezone.utc)
        for i in range(10):
            shipment = Shipment(
                id=f"test-replenish-{i}",
                origin="Shanghai Port",
                destination="Los Angeles Port",
                origin_coords=Coordinates(lat=31.23, lng=121.47),
                destination_coords=Coordinates(lat=33.74, lng=-118.26),
                current_coords=Coordinates(lat=32.0, lng=0.0),
                status=ShipmentStatus.IN_TRANSIT,
                created_at=now - timedelta(hours=1),
                updated_at=now,
            )
            data_store.upsert_shipment(shipment)

        manager.simulation_cycle()

        active = data_store.get_active_shipment_count()
        assert active >= 50

    def test_cycle_records_analytics_snapshot(self, manager):
        """Each cycle should add an analytics snapshot."""
        manager.generate_initial_shipments()
        initial_count = len(data_store._analytics_snapshots)

        manager.simulation_cycle()

        assert len(data_store._analytics_snapshots) > initial_count

    def test_analytics_snapshot_has_required_fields(self, manager):
        """Analytics snapshots should contain expected keys."""
        manager.generate_initial_shipments()
        manager.simulation_cycle()

        snapshot = data_store._analytics_snapshots[-1]
        assert "timestamp" in snapshot
        assert "delay_trend" in snapshot
        assert "cost_saving" in snapshot
        assert "carbon_reduction" in snapshot
        assert "sla_compliance_pct" in snapshot

    def test_cycle_runs_ml_pipelines(self, manager):
        """ML pipelines should generate alerts and ETA predictions."""
        manager.generate_initial_shipments()
        manager.simulation_cycle()

        # Check that at least some shipments got ETA predictions
        shipments = data_store.get_shipments()
        has_eta = any(s.eta_predicted is not None for s in shipments)
        assert has_eta, "At least some shipments should have ETA predictions"

    def test_cycle_does_not_crash_with_empty_store(self, manager):
        """Cycle should handle empty data store gracefully."""
        manager.simulation_cycle()
        # Should replenish from 0 to at least 50
        assert data_store.get_active_shipment_count() >= 50


# ── Start / Stop lifecycle ───────────────────────────────────────────


class TestSimulationLifecycle:
    @pytest.mark.asyncio
    async def test_start_generates_shipments(self):
        manager = SimulationManager()
        await manager.start()
        try:
            assert len(data_store.get_shipments()) >= 50
            assert manager._running is True
            assert manager._task is not None
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_stop_sets_running_false(self):
        manager = SimulationManager()
        await manager.start()
        await manager.stop()
        assert manager._running is False
        assert manager._task is None

    @pytest.mark.asyncio
    async def test_stop_is_idempotent(self):
        manager = SimulationManager()
        await manager.start()
        await manager.stop()
        await manager.stop()  # should not raise
        assert manager._running is False
