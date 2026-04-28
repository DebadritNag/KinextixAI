"""Thread-safe in-memory data store for the Kinetix AI backend.

Provides a singleton DataStore that manages all application state including
shipments, risk alerts, settings, and analytics snapshots. Write operations
are protected by a threading.Lock; reads are lock-free since Python's GIL
ensures atomic reference reads on dict/list objects.

Requirements: 15.3 (concurrent request handling), 20.3 (in-memory, no external DB)
"""

import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.models import (
    AnalyticsData,
    OptimizationWeights,
    RiskAlert,
    Settings,
    Shipment,
    ShipmentStatus,
)


class DataStore:
    """Thread-safe singleton managing all in-memory application state."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._shipments: dict[str, Shipment] = {}
        self._alerts: list[RiskAlert] = []
        self._settings: Settings = Settings(
            sla_thresholds={"standard": 72.0, "express": 24.0, "overnight": 12.0},
            penalties={"standard": 50.0, "express": 150.0, "overnight": 300.0},
            default_weights=OptimizationWeights(),
        )
        self._analytics_snapshots: list[dict] = []

    # ── Shipment operations ──────────────────────────────────────────

    def get_shipments(self) -> list[Shipment]:
        """Return all shipments as a list (lock-free read)."""
        return list(self._shipments.values())

    def get_shipment(self, shipment_id: str) -> Optional[Shipment]:
        """Return a single shipment by ID, or None if not found."""
        return self._shipments.get(shipment_id)

    def upsert_shipment(self, shipment: Shipment) -> None:
        """Insert or update a shipment (thread-safe write)."""
        with self._lock:
            self._shipments[shipment.id] = shipment

    def get_active_shipment_count(self) -> int:
        """Return the count of non-delivered shipments."""
        return sum(
            1
            for s in self._shipments.values()
            if s.status != ShipmentStatus.DELIVERED
        )

    # ── Alert operations ─────────────────────────────────────────────

    def get_alerts(self, severity: Optional[str] = None) -> list[RiskAlert]:
        """Return alerts, optionally filtered by severity string."""
        if severity is None:
            return list(self._alerts)
        return [a for a in self._alerts if a.severity.value == severity]

    def add_alert(self, alert: RiskAlert) -> None:
        """Append a new risk alert (thread-safe write)."""
        with self._lock:
            self._alerts.append(alert)

    def clear_alerts(self) -> None:
        """Remove all alerts (thread-safe write)."""
        with self._lock:
            self._alerts.clear()

    # ── Settings operations ──────────────────────────────────────────

    def get_settings(self) -> Settings:
        """Return the current settings (lock-free read)."""
        return self._settings

    def update_settings(self, settings: Settings) -> None:
        """Replace the current settings (thread-safe write)."""
        with self._lock:
            self._settings = settings

    # ── Analytics operations ─────────────────────────────────────────

    def add_analytics_snapshot(self, snapshot: dict) -> None:
        """Record an analytics data point from the simulation loop."""
        with self._lock:
            self._analytics_snapshots.append(snapshot)

    def get_analytics(self, time_range: str) -> AnalyticsData:
        """Return analytics data filtered by time range.

        Supported ranges: "24h", "7d", "30d".
        Snapshots are filtered by their "timestamp" key.
        If no snapshots match, empty lists are returned with 0.0 compliance.
        """
        now = datetime.now(timezone.utc)
        hours_map = {"24h": 24, "7d": 168, "30d": 720}
        hours = hours_map.get(time_range, 24)
        cutoff = now - timedelta(hours=hours)

        filtered = [
            s
            for s in self._analytics_snapshots
            if s.get("timestamp", now) >= cutoff
        ]

        delay_trends: list[dict] = []
        cost_savings: list[dict] = []
        carbon_reduction: list[dict] = []
        sla_trend: list[dict] = []
        sla_compliance_values: list[float] = []

        for snap in filtered:
            if "delay_trend" in snap:
                delay_trends.append(snap["delay_trend"])
            if "cost_saving" in snap:
                cost_savings.append(snap["cost_saving"])
            if "carbon_reduction" in snap:
                carbon_reduction.append(snap["carbon_reduction"])
            if "sla_compliance_pct" in snap:
                sla_compliance_values.append(snap["sla_compliance_pct"])
                sla_trend.append(
                    {
                        "date": snap.get("timestamp", now).isoformat(),
                        "compliance_pct": snap["sla_compliance_pct"],
                    }
                )

        avg_compliance = (
            sum(sla_compliance_values) / len(sla_compliance_values)
            if sla_compliance_values
            else 0.0
        )

        return AnalyticsData(
            delay_trends=delay_trends,
            cost_savings=cost_savings,
            carbon_reduction=carbon_reduction,
            sla_compliance_pct=avg_compliance,
            sla_trend=sla_trend,
        )


# Module-level singleton instance
data_store = DataStore()
