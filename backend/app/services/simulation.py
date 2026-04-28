"""Simulation loop for generating and updating mock supply chain data.

Manages the lifecycle of simulated shipments: generates an initial pool,
advances positions, injects random events, delivers completed shipments,
replenishes the pool, runs ML pipelines, and records analytics snapshots.

Requirements: 14.1, 14.2, 14.3, 14.4, 14.5
"""

import asyncio
import logging
import math
import random
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.models import Coordinates, Shipment, ShipmentStatus, TimelineEvent
from app.services.data_store import data_store
from app.services.disruption_detector import DisruptionDetector, _haversine_km
from app.services.eta_predictor import ETAPredictor
from app.services.optimization_engine import _NODES

logger = logging.getLogger("kinetix.simulation")

# ── Constants ────────────────────────────────────────────────────────

_WEATHER_CONDITIONS = ["clear", "rain", "storm", "severe"]
_WEATHER_WEIGHTS = [0.6, 0.25, 0.1, 0.05]

_STATUS_CHOICES = [
    ShipmentStatus.IN_TRANSIT,
    ShipmentStatus.CREATED,
    ShipmentStatus.DELAYED,
    ShipmentStatus.DELIVERED,
]
_STATUS_WEIGHTS = [0.60, 0.20, 0.10, 0.10]

_MIN_ACTIVE = 50
_MAX_ACTIVE = 100
_NEAR_DESTINATION_KM = 50.0

# Event injection probabilities per shipment per cycle
_PROB_WEATHER_CHANGE = 0.05
_PROB_RANDOM_DELAY = 0.05
_PROB_ROUTE_DEVIATION = 0.02
_PROB_STATUS_RECOVERY = 0.03


# ── Helpers ──────────────────────────────────────────────────────────


def _random_node() -> dict:
    """Return a random node from the logistics graph."""
    return random.choice(_NODES)


def _random_node_pair() -> tuple[dict, dict]:
    """Return two distinct random nodes for origin and destination."""
    origin = _random_node()
    destination = _random_node()
    while destination["id"] == origin["id"]:
        destination = _random_node()
    return origin, destination


def _interpolate_coords(
    origin: Coordinates, destination: Coordinates, fraction: float
) -> Coordinates:
    """Linearly interpolate between origin and destination coordinates."""
    fraction = max(0.0, min(1.0, fraction))
    lat = origin.lat + fraction * (destination.lat - origin.lat)
    lng = origin.lng + fraction * (destination.lng - origin.lng)
    return Coordinates(lat=lat, lng=lng)


def _build_shipment(
    origin_node: dict,
    dest_node: dict,
    status: ShipmentStatus,
    position_fraction: float,
) -> Shipment:
    """Create a Shipment with the given parameters."""
    now = datetime.now(timezone.utc)
    origin_coords = Coordinates(**origin_node["coords"])
    dest_coords = Coordinates(**dest_node["coords"])
    current_coords = _interpolate_coords(origin_coords, dest_coords, position_fraction)

    # Randomise creation time in the past (1-72 hours ago)
    created_at = now - timedelta(hours=random.uniform(1, 72))

    weather = random.choices(_WEATHER_CONDITIONS, weights=_WEATHER_WEIGHTS, k=1)[0]
    delay = random.randint(0, 120) if status == ShipmentStatus.DELAYED else 0

    shipment = Shipment(
        id=str(uuid4()),
        origin=origin_node["name"],
        destination=dest_node["name"],
        origin_coords=origin_coords,
        destination_coords=dest_coords,
        current_coords=current_coords,
        status=status,
        created_at=created_at,
        updated_at=now,
        delay_minutes=delay,
        weather_condition=weather,
        timeline=[
            TimelineEvent(
                timestamp=created_at,
                event="Shipment created",
                location=origin_node["name"],
            )
        ],
    )
    return shipment


# ── SimulationManager ────────────────────────────────────────────────


class SimulationManager:
    """Manages the simulation lifecycle: init, run, stop.

    Usage::

        manager = SimulationManager()
        await manager.start()   # generates shipments, starts background loop
        ...
        await manager.stop()    # gracefully stops the loop
    """

    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task | None = None
        self._detector = DisruptionDetector()
        self._eta_predictor = ETAPredictor()

    # ── Public API ───────────────────────────────────────────────────

    async def start(self) -> None:
        """Generate initial shipments, run ML pipelines, start the loop."""
        logger.info("Simulation starting...")
        self.generate_initial_shipments()
        self._run_ml_pipelines()
        self._running = True
        self._task = asyncio.create_task(self._simulation_loop())
        logger.info("Simulation loop started.")

    async def stop(self) -> None:
        """Gracefully stop the simulation loop."""
        logger.info("Stopping simulation loop...")
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Simulation loop stopped.")

    # ── Initialization ───────────────────────────────────────────────

    def generate_initial_shipments(self) -> None:
        """Generate 50-100 shipments with randomized attributes.

        Status distribution: 60% in_transit, 20% created, 10% delayed,
        10% delivered.
        """
        count = random.randint(_MIN_ACTIVE, _MAX_ACTIVE)
        logger.info("Generating %d initial shipments...", count)

        for _ in range(count):
            origin_node, dest_node = _random_node_pair()
            status = random.choices(_STATUS_CHOICES, weights=_STATUS_WEIGHTS, k=1)[0]

            # Position fraction depends on status
            if status == ShipmentStatus.CREATED:
                fraction = 0.0
            elif status == ShipmentStatus.DELIVERED:
                fraction = 1.0
            elif status == ShipmentStatus.IN_TRANSIT:
                fraction = random.uniform(0.05, 0.95)
            else:  # DELAYED
                fraction = random.uniform(0.1, 0.8)

            shipment = _build_shipment(origin_node, dest_node, status, fraction)
            data_store.upsert_shipment(shipment)

        logger.info("Generated %d shipments.", count)

    # ── Background loop ──────────────────────────────────────────────

    async def _simulation_loop(self) -> None:
        """Background loop that runs simulation cycles at random intervals."""
        while self._running:
            interval = random.uniform(10, 20)
            await asyncio.sleep(interval)
            if not self._running:
                break
            self.simulation_cycle()

    def simulation_cycle(self) -> None:
        """Execute one simulation update cycle.

        Steps:
        1. Advance shipment positions (in_transit shipments)
        2. Inject random events
        3. Deliver completed shipments (near destination)
        4. Replenish pool to maintain 50-100 active
        5. Run ML pipelines
        6. Record analytics snapshot
        """
        now = datetime.now(timezone.utc)

        # 1. Advance positions
        for shipment in data_store.get_shipments():
            if shipment.status == ShipmentStatus.IN_TRANSIT:
                self._advance_position(shipment, now)

        # 2. Inject random events
        for shipment in data_store.get_shipments():
            if shipment.status in (
                ShipmentStatus.IN_TRANSIT,
                ShipmentStatus.DELAYED,
                ShipmentStatus.CREATED,
            ):
                self._inject_events(shipment, now)

        # 3. Deliver completed shipments
        for shipment in data_store.get_shipments():
            if shipment.status == ShipmentStatus.IN_TRANSIT:
                dist = _haversine_km(shipment.current_coords, shipment.destination_coords)
                if dist < _NEAR_DESTINATION_KM:
                    shipment.status = ShipmentStatus.DELIVERED
                    shipment.current_coords = shipment.destination_coords.model_copy()
                    shipment.updated_at = now
                    shipment.delay_minutes = 0
                    shipment.timeline.append(
                        TimelineEvent(
                            timestamp=now,
                            event="Shipment delivered",
                            location=shipment.destination,
                        )
                    )
                    data_store.upsert_shipment(shipment)

        # 4. Replenish pool
        self._replenish_pool()

        # 5. Run ML pipelines
        self._run_ml_pipelines()

        # 6. Record analytics snapshot
        self._record_analytics_snapshot(now)

        logger.info("Simulation cycle complete.")

    # ── Position advancement ─────────────────────────────────────────

    def _advance_position(self, shipment: Shipment, now: datetime) -> None:
        """Move an in-transit shipment along its route via linear interpolation."""
        created = shipment.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)

        # Estimate total transit time (48h default, adjusted by distance)
        total_dist = _haversine_km(shipment.origin_coords, shipment.destination_coords)
        # ~40 km/h average speed
        transit_hours = max(total_dist / 40.0, 1.0)
        total_seconds = transit_hours * 3600

        elapsed = (now - created).total_seconds()
        fraction = max(0.0, min(1.0, elapsed / total_seconds))

        shipment.current_coords = _interpolate_coords(
            shipment.origin_coords, shipment.destination_coords, fraction
        )
        shipment.updated_at = now
        data_store.upsert_shipment(shipment)

    # ── Event injection ──────────────────────────────────────────────

    def _inject_events(self, shipment: Shipment, now: datetime) -> None:
        """Inject random events into a shipment based on configured probabilities."""
        # Weather change (5%)
        if random.random() < _PROB_WEATHER_CHANGE:
            old_weather = shipment.weather_condition
            new_weather = random.choices(
                _WEATHER_CONDITIONS, weights=[0.3, 0.35, 0.25, 0.1], k=1
            )[0]
            shipment.weather_condition = new_weather
            if new_weather in ("storm", "severe"):
                shipment.delay_minutes += random.randint(15, 60)
            shipment.updated_at = now
            shipment.timeline.append(
                TimelineEvent(
                    timestamp=now,
                    event=f"Weather changed from {old_weather} to {new_weather}",
                    details=f"Delay: {shipment.delay_minutes}min",
                )
            )
            data_store.upsert_shipment(shipment)

        # Random delay (5%)
        if random.random() < _PROB_RANDOM_DELAY:
            added_delay = random.randint(30, 180)
            shipment.delay_minutes += added_delay
            if shipment.status == ShipmentStatus.IN_TRANSIT:
                shipment.status = ShipmentStatus.DELAYED
            shipment.updated_at = now
            shipment.timeline.append(
                TimelineEvent(
                    timestamp=now,
                    event=f"Random delay: +{added_delay}min",
                    details=f"Total delay: {shipment.delay_minutes}min",
                )
            )
            data_store.upsert_shipment(shipment)

        # Route deviation (2%)
        if random.random() < _PROB_ROUTE_DEVIATION:
            lat_offset = random.uniform(-0.5, 0.5)
            lng_offset = random.uniform(-0.5, 0.5)
            new_lat = max(-90, min(90, shipment.current_coords.lat + lat_offset))
            new_lng = max(-180, min(180, shipment.current_coords.lng + lng_offset))
            shipment.current_coords = Coordinates(lat=new_lat, lng=new_lng)
            shipment.updated_at = now
            shipment.timeline.append(
                TimelineEvent(
                    timestamp=now,
                    event="Route deviation detected",
                    details=f"Offset: ({lat_offset:.2f}, {lng_offset:.2f})",
                )
            )
            data_store.upsert_shipment(shipment)

        # Status recovery (3% for delayed shipments)
        if (
            shipment.status == ShipmentStatus.DELAYED
            and random.random() < _PROB_STATUS_RECOVERY
        ):
            reduction = random.randint(30, min(120, shipment.delay_minutes))
            shipment.delay_minutes = max(0, shipment.delay_minutes - reduction)
            if shipment.delay_minutes == 0:
                shipment.status = ShipmentStatus.IN_TRANSIT
                shipment.weather_condition = "clear"
            else:
                # Improve weather
                shipment.weather_condition = random.choice(["clear", "rain"])
            shipment.updated_at = now
            shipment.timeline.append(
                TimelineEvent(
                    timestamp=now,
                    event=f"Recovery: delay reduced by {reduction}min",
                    details=f"Remaining delay: {shipment.delay_minutes}min",
                )
            )
            data_store.upsert_shipment(shipment)

    # ── Pool replenishment ───────────────────────────────────────────

    def _replenish_pool(self) -> None:
        """Add new shipments to maintain 50-100 active shipments."""
        active_count = data_store.get_active_shipment_count()
        if active_count < _MIN_ACTIVE:
            needed = _MIN_ACTIVE - active_count
            logger.info("Replenishing pool: adding %d shipments.", needed)
            for _ in range(needed):
                origin_node, dest_node = _random_node_pair()
                # New shipments start as in_transit or created
                status = random.choices(
                    [ShipmentStatus.IN_TRANSIT, ShipmentStatus.CREATED],
                    weights=[0.75, 0.25],
                    k=1,
                )[0]
                fraction = 0.0 if status == ShipmentStatus.CREATED else random.uniform(0.0, 0.2)
                shipment = _build_shipment(origin_node, dest_node, status, fraction)
                data_store.upsert_shipment(shipment)

    # ── ML pipelines ─────────────────────────────────────────────────

    def _run_ml_pipelines(self) -> None:
        """Run disruption detection and ETA prediction on active shipments."""
        active = [
            s
            for s in data_store.get_shipments()
            if s.status != ShipmentStatus.DELIVERED
        ]
        if not active:
            return

        # Disruption detection
        alerts = self._detector.analyze_batch(active)
        for alert in alerts:
            data_store.add_alert(alert)

        # ETA prediction
        for shipment in active:
            prediction = self._eta_predictor.predict(shipment)
            shipment.eta_predicted = prediction.predicted_arrival
            shipment.eta_confidence_low = prediction.confidence_low
            shipment.eta_confidence_high = prediction.confidence_high
            shipment.updated_at = datetime.now(timezone.utc)
            data_store.upsert_shipment(shipment)

    # ── Analytics recording ──────────────────────────────────────────

    def _record_analytics_snapshot(self, now: datetime) -> None:
        """Record a point-in-time analytics snapshot."""
        shipments = data_store.get_shipments()
        total = len(shipments)
        if total == 0:
            return

        delivered = sum(1 for s in shipments if s.status == ShipmentStatus.DELIVERED)
        delayed = sum(1 for s in shipments if s.status == ShipmentStatus.DELAYED)
        in_transit = sum(1 for s in shipments if s.status == ShipmentStatus.IN_TRANSIT)

        avg_delay = (
            sum(s.delay_minutes for s in shipments if s.delay_minutes > 0)
            / max(1, sum(1 for s in shipments if s.delay_minutes > 0))
        )

        # SLA compliance: shipments not delayed / total non-delivered
        non_delivered = total - delivered
        on_time = non_delivered - delayed
        sla_pct = (on_time / non_delivered * 100) if non_delivered > 0 else 100.0

        snapshot = {
            "timestamp": now,
            "delay_trend": {
                "date": now.isoformat(),
                "avg_delay_minutes": round(avg_delay, 1),
                "delayed_count": delayed,
            },
            "cost_saving": {
                "date": now.isoformat(),
                "optimized_cost": round(random.uniform(8000, 12000), 2),
                "baseline_cost": round(random.uniform(12000, 18000), 2),
            },
            "carbon_reduction": {
                "date": now.isoformat(),
                "optimized_kg": round(random.uniform(3000, 5000), 2),
                "baseline_kg": round(random.uniform(5000, 8000), 2),
            },
            "sla_compliance_pct": round(sla_pct, 1),
            "total_shipments": total,
            "delivered": delivered,
            "in_transit": in_transit,
            "delayed": delayed,
        }
        data_store.add_analytics_snapshot(snapshot)
