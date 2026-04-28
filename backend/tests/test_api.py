"""API endpoint tests for the Kinetix AI backend.

Uses a standalone FastAPI app (no lifespan/simulation) to test all
API routers in isolation.
"""

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.alerts import router as alerts_router
from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.demo import router as demo_router
from app.api.explain import router as explain_router
from app.api.optimize import router as optimize_router
from app.api.settings import router as settings_router
from app.api.shipments import router as shipments_router
from app.models import (
    Coordinates,
    Shipment,
    ShipmentStatus,
)
from app.services.data_store import data_store


def _create_test_app() -> FastAPI:
    """Create a minimal FastAPI app with all routers but no lifespan."""
    test_app = FastAPI()
    test_app.include_router(shipments_router)
    test_app.include_router(alerts_router)
    test_app.include_router(optimize_router)
    test_app.include_router(explain_router)
    test_app.include_router(analytics_router)
    test_app.include_router(settings_router)
    test_app.include_router(auth_router)
    test_app.include_router(demo_router)
    return test_app


@pytest.fixture()
def client():
    """Provide a TestClient with a clean data store for each test."""
    # Reset data store state
    data_store._shipments.clear()
    data_store._alerts.clear()
    data_store._analytics_snapshots.clear()

    app = _create_test_app()
    with TestClient(app) as c:
        yield c


def _seed_shipment(shipment_id: str = "SHP-001") -> Shipment:
    """Insert a test shipment into the data store and return it."""
    now = datetime.now(timezone.utc)
    shipment = Shipment(
        id=shipment_id,
        origin="Shanghai Port",
        destination="Rotterdam DC",
        origin_coords=Coordinates(lat=31.23, lng=121.47),
        destination_coords=Coordinates(lat=51.95, lng=4.50),
        current_coords=Coordinates(lat=35.0, lng=100.0),
        status=ShipmentStatus.IN_TRANSIT,
        created_at=now,
        updated_at=now,
        delay_minutes=0,
        weather_condition="clear",
    )
    data_store.upsert_shipment(shipment)
    return shipment


# ── Shipment endpoints ───────────────────────────────────────────────


class TestShipments:
    def test_list_shipments_empty(self, client: TestClient):
        resp = client.get("/api/shipments")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["data"] == []
        assert body["error"] is None
        assert "timestamp" in body

    def test_list_shipments_with_data(self, client: TestClient):
        _seed_shipment("SHP-001")
        _seed_shipment("SHP-002")
        resp = client.get("/api/shipments")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 2

    def test_get_shipment_found(self, client: TestClient):
        _seed_shipment("SHP-001")
        resp = client.get("/api/shipments/SHP-001")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["id"] == "SHP-001"
        assert body["data"]["origin"] == "Shanghai Port"

    def test_get_shipment_not_found(self, client: TestClient):
        resp = client.get("/api/shipments/NONEXISTENT")
        assert resp.status_code == 404


# ── Alert endpoints ──────────────────────────────────────────────────


class TestAlerts:
    def test_list_alerts_empty(self, client: TestClient):
        resp = client.get("/api/alerts")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["data"] == []

    def test_list_alerts_with_data(self, client: TestClient):
        from app.models.alert import RiskAlert, Severity

        alert = RiskAlert(
            id="ALT-001",
            shipment_id="SHP-001",
            severity=Severity.HIGH,
            title="Test alert",
            description="Test description",
            created_at=datetime.now(timezone.utc),
            is_active=True,
        )
        data_store.add_alert(alert)
        resp = client.get("/api/alerts")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 1
        assert body["data"][0]["severity"] == "high"


# ── Auth endpoints ───────────────────────────────────────────────────


class TestAuth:
    def test_login(self, client: TestClient):
        resp = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "secret"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert "token" in body["data"]
        assert body["data"]["user"]["username"] == "admin"

    def test_logout(self, client: TestClient):
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["data"]["message"] == "Logged out successfully"


# ── Analytics endpoint ───────────────────────────────────────────────


class TestAnalytics:
    def test_get_analytics_default(self, client: TestClient):
        resp = client.get("/api/analytics")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert "delay_trends" in body["data"]
        assert "sla_compliance_pct" in body["data"]

    def test_get_analytics_with_time_range(self, client: TestClient):
        resp = client.get("/api/analytics?time_range=7d")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"


# ── Settings endpoints ───────────────────────────────────────────────


class TestSettings:
    def test_get_settings(self, client: TestClient):
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert "sla_thresholds" in body["data"]
        assert "default_weights" in body["data"]

    def test_update_settings(self, client: TestClient):
        new_settings = {
            "sla_thresholds": {"standard": 80.0, "express": 30.0, "overnight": 15.0},
            "penalties": {"standard": 60.0, "express": 200.0, "overnight": 400.0},
            "default_weights": {
                "cost": 0.4,
                "time": 0.3,
                "carbon": 0.2,
                "risk": 0.1,
            },
        }
        resp = client.put("/api/settings", json=new_settings)
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["sla_thresholds"]["standard"] == 80.0
        assert body["data"]["default_weights"]["cost"] == 0.4


# ── Optimize endpoint ────────────────────────────────────────────────


class TestOptimize:
    def test_optimize_shipment_not_found(self, client: TestClient):
        resp = client.post(
            "/api/optimize",
            json={
                "shipment_id": "NONEXISTENT",
                "weights": {"cost": 0.25, "time": 0.25, "carbon": 0.25, "risk": 0.25},
            },
        )
        assert resp.status_code == 404

    def test_optimize_with_valid_shipment(self, client: TestClient):
        # Seed a shipment whose origin/destination map to graph nodes
        now = datetime.now(timezone.utc)
        shipment = Shipment(
            id="SHP-OPT",
            origin="shanghai_port",
            destination="rotterdam_dc",
            origin_coords=Coordinates(lat=31.23, lng=121.47),
            destination_coords=Coordinates(lat=51.95, lng=4.50),
            current_coords=Coordinates(lat=35.0, lng=100.0),
            status=ShipmentStatus.IN_TRANSIT,
            created_at=now,
            updated_at=now,
        )
        data_store.upsert_shipment(shipment)

        resp = client.post(
            "/api/optimize",
            json={
                "shipment_id": "SHP-OPT",
                "weights": {"cost": 0.25, "time": 0.25, "carbon": 0.25, "risk": 0.25},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert "routes" in body["data"]
        assert "computation_time_ms" in body["data"]


# ── Explain endpoint ─────────────────────────────────────────────────


class TestExplain:
    def test_explain_fallback(self, client: TestClient):
        """Explain endpoint returns a valid explanation (model or fallback)."""
        resp = client.post(
            "/api/explain",
            json={
                "route": {
                    "route_id": "r1",
                    "waypoints": ["shanghai_port", "singapore_port", "rotterdam_port"],
                    "label": "cheapest",
                    "cost_usd": 3000.0,
                    "eta_hours": 240.0,
                    "carbon_kg": 770.0,
                    "risk_score": 40.0,
                    "score": 0.45,
                    "is_recommended": True,
                },
                "alternatives": [],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert "explanation" in body["data"]
        assert body["data"]["source"] in ("model", "fallback")


# ── Demo endpoint ────────────────────────────────────────────────────


class TestDemo:
    def test_trigger_disruption_not_found(self, client: TestClient):
        resp = client.post(
            "/api/demo/trigger-disruption",
            json={"shipment_id": "NONEXISTENT"},
        )
        assert resp.status_code == 404

    def test_trigger_disruption_success(self, client: TestClient):
        _seed_shipment("SHP-DEMO")
        resp = client.post(
            "/api/demo/trigger-disruption",
            json={"shipment_id": "SHP-DEMO"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["data"]["shipment_id"] == "SHP-DEMO"
        assert body["data"]["severity"] == "high"

        # Verify the alert was added to the data store
        alerts = data_store.get_alerts()
        assert len(alerts) >= 1
        assert any(a.shipment_id == "SHP-DEMO" for a in alerts)
