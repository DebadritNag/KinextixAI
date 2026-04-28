"""Optimization Engine for computing optimal supply chain routes.

Models the global logistics network as a directed graph using NetworkX.
Computes weighted multi-objective route scores across cost, time, carbon,
and risk dimensions with min-max normalization.

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7
"""

import uuid

import networkx as nx

from app.models import OptimizationWeights, RouteOption, Settings


# ── Node definitions ─────────────────────────────────────────────────

_NODES: list[dict] = [
    {"id": "shanghai_port", "name": "Shanghai Port", "type": "port", "coords": {"lat": 31.23, "lng": 121.47}},
    {"id": "singapore_port", "name": "Singapore Port", "type": "port", "coords": {"lat": 1.26, "lng": 103.84}},
    {"id": "dubai_port", "name": "Dubai Port", "type": "port", "coords": {"lat": 25.27, "lng": 55.29}},
    {"id": "rotterdam_port", "name": "Rotterdam Port", "type": "port", "coords": {"lat": 51.92, "lng": 4.48}},
    {"id": "hamburg_port", "name": "Hamburg Port", "type": "port", "coords": {"lat": 53.55, "lng": 9.99}},
    {"id": "la_port", "name": "Los Angeles Port", "type": "port", "coords": {"lat": 33.74, "lng": -118.26}},
    {"id": "ny_port", "name": "New York Port", "type": "port", "coords": {"lat": 40.68, "lng": -74.04}},
    {"id": "busan_port", "name": "Busan Port", "type": "port", "coords": {"lat": 35.10, "lng": 129.04}},
    {"id": "mumbai_port", "name": "Mumbai Port", "type": "port", "coords": {"lat": 18.95, "lng": 72.84}},
    {"id": "shanghai_wh", "name": "Shanghai Warehouse", "type": "warehouse", "coords": {"lat": 31.30, "lng": 121.50}},
    {"id": "singapore_wh", "name": "Singapore Warehouse", "type": "warehouse", "coords": {"lat": 1.30, "lng": 103.80}},
    {"id": "dubai_wh", "name": "Dubai Warehouse", "type": "warehouse", "coords": {"lat": 25.20, "lng": 55.35}},
    {"id": "rotterdam_dc", "name": "Rotterdam Distribution Center", "type": "distribution_center", "coords": {"lat": 51.95, "lng": 4.50}},
    {"id": "hamburg_dc", "name": "Hamburg Distribution Center", "type": "distribution_center", "coords": {"lat": 53.60, "lng": 10.00}},
    {"id": "la_dc", "name": "Los Angeles Distribution Center", "type": "distribution_center", "coords": {"lat": 33.80, "lng": -118.20}},
    {"id": "ny_dc", "name": "New York Distribution Center", "type": "distribution_center", "coords": {"lat": 40.75, "lng": -74.00}},
    {"id": "chicago_dc", "name": "Chicago Distribution Center", "type": "distribution_center", "coords": {"lat": 41.88, "lng": -87.63}},
    {"id": "suez_customs", "name": "Suez Canal Customs", "type": "customs", "coords": {"lat": 30.00, "lng": 32.58}},
    {"id": "panama_customs", "name": "Panama Canal Customs", "type": "customs", "coords": {"lat": 9.08, "lng": -79.68}},
    {"id": "shenzhen_port", "name": "Shenzhen Port", "type": "port", "coords": {"lat": 22.54, "lng": 114.06}},
    {"id": "tokyo_port", "name": "Tokyo Port", "type": "port", "coords": {"lat": 35.65, "lng": 139.77}},
    {"id": "london_dc", "name": "London Distribution Center", "type": "distribution_center", "coords": {"lat": 51.51, "lng": -0.13}},
]

# ── Edge definitions ─────────────────────────────────────────────────
# Each tuple: (source, target, {cost_usd, time_hours, carbon_kg, risk_score, transport_mode})

_EDGES: list[tuple[str, str, dict]] = [
    # Shanghai hub connections
    ("shanghai_port", "shanghai_wh", {"cost_usd": 80.0, "time_hours": 4.0, "carbon_kg": 15.0, "risk_score": 5.0, "transport_mode": "road"}),
    ("shanghai_wh", "shanghai_port", {"cost_usd": 80.0, "time_hours": 4.0, "carbon_kg": 15.0, "risk_score": 5.0, "transport_mode": "road"}),
    ("shanghai_port", "singapore_port", {"cost_usd": 1200.0, "time_hours": 96.0, "carbon_kg": 320.0, "risk_score": 20.0, "transport_mode": "sea"}),
    ("shanghai_port", "busan_port", {"cost_usd": 600.0, "time_hours": 36.0, "carbon_kg": 150.0, "risk_score": 10.0, "transport_mode": "sea"}),
    ("shanghai_port", "la_port", {"cost_usd": 3500.0, "time_hours": 288.0, "carbon_kg": 850.0, "risk_score": 35.0, "transport_mode": "sea"}),
    ("shanghai_port", "tokyo_port", {"cost_usd": 800.0, "time_hours": 48.0, "carbon_kg": 200.0, "risk_score": 12.0, "transport_mode": "sea"}),
    ("shanghai_port", "shenzhen_port", {"cost_usd": 400.0, "time_hours": 24.0, "carbon_kg": 100.0, "risk_score": 8.0, "transport_mode": "sea"}),

    # Shenzhen connections
    ("shenzhen_port", "singapore_port", {"cost_usd": 1000.0, "time_hours": 72.0, "carbon_kg": 280.0, "risk_score": 18.0, "transport_mode": "sea"}),
    ("shenzhen_port", "la_port", {"cost_usd": 3800.0, "time_hours": 300.0, "carbon_kg": 900.0, "risk_score": 38.0, "transport_mode": "sea"}),

    # Singapore hub connections
    ("singapore_port", "singapore_wh", {"cost_usd": 60.0, "time_hours": 3.0, "carbon_kg": 10.0, "risk_score": 3.0, "transport_mode": "road"}),
    ("singapore_wh", "singapore_port", {"cost_usd": 60.0, "time_hours": 3.0, "carbon_kg": 10.0, "risk_score": 3.0, "transport_mode": "road"}),
    ("singapore_port", "dubai_port", {"cost_usd": 1800.0, "time_hours": 144.0, "carbon_kg": 450.0, "risk_score": 25.0, "transport_mode": "sea"}),
    ("singapore_port", "mumbai_port", {"cost_usd": 1400.0, "time_hours": 120.0, "carbon_kg": 380.0, "risk_score": 22.0, "transport_mode": "sea"}),
    ("singapore_port", "suez_customs", {"cost_usd": 2800.0, "time_hours": 240.0, "carbon_kg": 650.0, "risk_score": 40.0, "transport_mode": "sea"}),

    # Dubai hub connections
    ("dubai_port", "dubai_wh", {"cost_usd": 70.0, "time_hours": 3.0, "carbon_kg": 12.0, "risk_score": 4.0, "transport_mode": "road"}),
    ("dubai_wh", "dubai_port", {"cost_usd": 70.0, "time_hours": 3.0, "carbon_kg": 12.0, "risk_score": 4.0, "transport_mode": "road"}),
    ("dubai_port", "suez_customs", {"cost_usd": 900.0, "time_hours": 72.0, "carbon_kg": 220.0, "risk_score": 30.0, "transport_mode": "sea"}),
    ("dubai_port", "mumbai_port", {"cost_usd": 1100.0, "time_hours": 96.0, "carbon_kg": 300.0, "risk_score": 20.0, "transport_mode": "sea"}),
    ("dubai_port", "rotterdam_port", {"cost_usd": 2200.0, "time_hours": 192.0, "carbon_kg": 520.0, "risk_score": 28.0, "transport_mode": "sea"}),

    # Suez Canal connections
    ("suez_customs", "rotterdam_port", {"cost_usd": 1500.0, "time_hours": 168.0, "carbon_kg": 400.0, "risk_score": 35.0, "transport_mode": "sea"}),
    ("suez_customs", "hamburg_port", {"cost_usd": 1600.0, "time_hours": 180.0, "carbon_kg": 420.0, "risk_score": 33.0, "transport_mode": "sea"}),

    # Mumbai connections
    ("mumbai_port", "dubai_port", {"cost_usd": 1100.0, "time_hours": 96.0, "carbon_kg": 300.0, "risk_score": 20.0, "transport_mode": "sea"}),
    ("mumbai_port", "suez_customs", {"cost_usd": 2000.0, "time_hours": 192.0, "carbon_kg": 500.0, "risk_score": 32.0, "transport_mode": "sea"}),
    ("mumbai_port", "singapore_port", {"cost_usd": 1400.0, "time_hours": 120.0, "carbon_kg": 380.0, "risk_score": 22.0, "transport_mode": "sea"}),

    # Rotterdam hub connections
    ("rotterdam_port", "rotterdam_dc", {"cost_usd": 90.0, "time_hours": 2.0, "carbon_kg": 8.0, "risk_score": 3.0, "transport_mode": "road"}),
    ("rotterdam_dc", "rotterdam_port", {"cost_usd": 90.0, "time_hours": 2.0, "carbon_kg": 8.0, "risk_score": 3.0, "transport_mode": "road"}),
    ("rotterdam_port", "hamburg_port", {"cost_usd": 350.0, "time_hours": 12.0, "carbon_kg": 45.0, "risk_score": 5.0, "transport_mode": "rail"}),
    ("rotterdam_dc", "hamburg_dc", {"cost_usd": 300.0, "time_hours": 8.0, "carbon_kg": 35.0, "risk_score": 4.0, "transport_mode": "rail"}),
    ("rotterdam_dc", "london_dc", {"cost_usd": 450.0, "time_hours": 10.0, "carbon_kg": 55.0, "risk_score": 6.0, "transport_mode": "rail"}),

    # Hamburg hub connections
    ("hamburg_port", "hamburg_dc", {"cost_usd": 85.0, "time_hours": 2.0, "carbon_kg": 8.0, "risk_score": 3.0, "transport_mode": "road"}),
    ("hamburg_dc", "hamburg_port", {"cost_usd": 85.0, "time_hours": 2.0, "carbon_kg": 8.0, "risk_score": 3.0, "transport_mode": "road"}),
    ("hamburg_port", "rotterdam_port", {"cost_usd": 350.0, "time_hours": 12.0, "carbon_kg": 45.0, "risk_score": 5.0, "transport_mode": "rail"}),
    ("hamburg_dc", "london_dc", {"cost_usd": 500.0, "time_hours": 14.0, "carbon_kg": 60.0, "risk_score": 7.0, "transport_mode": "rail"}),

    # LA hub connections
    ("la_port", "la_dc", {"cost_usd": 100.0, "time_hours": 3.0, "carbon_kg": 18.0, "risk_score": 4.0, "transport_mode": "road"}),
    ("la_dc", "la_port", {"cost_usd": 100.0, "time_hours": 3.0, "carbon_kg": 18.0, "risk_score": 4.0, "transport_mode": "road"}),
    ("la_dc", "chicago_dc", {"cost_usd": 800.0, "time_hours": 36.0, "carbon_kg": 120.0, "risk_score": 12.0, "transport_mode": "rail"}),
    ("la_dc", "ny_dc", {"cost_usd": 1200.0, "time_hours": 72.0, "carbon_kg": 180.0, "risk_score": 15.0, "transport_mode": "rail"}),
    ("la_port", "panama_customs", {"cost_usd": 2000.0, "time_hours": 168.0, "carbon_kg": 480.0, "risk_score": 30.0, "transport_mode": "sea"}),

    # NY hub connections
    ("ny_port", "ny_dc", {"cost_usd": 110.0, "time_hours": 3.0, "carbon_kg": 20.0, "risk_score": 5.0, "transport_mode": "road"}),
    ("ny_dc", "ny_port", {"cost_usd": 110.0, "time_hours": 3.0, "carbon_kg": 20.0, "risk_score": 5.0, "transport_mode": "road"}),
    ("ny_dc", "chicago_dc", {"cost_usd": 650.0, "time_hours": 24.0, "carbon_kg": 95.0, "risk_score": 10.0, "transport_mode": "rail"}),
    ("ny_port", "rotterdam_port", {"cost_usd": 2500.0, "time_hours": 192.0, "carbon_kg": 580.0, "risk_score": 25.0, "transport_mode": "sea"}),

    # Panama Canal connections
    ("panama_customs", "ny_port", {"cost_usd": 1800.0, "time_hours": 144.0, "carbon_kg": 420.0, "risk_score": 28.0, "transport_mode": "sea"}),
    ("panama_customs", "rotterdam_port", {"cost_usd": 2800.0, "time_hours": 240.0, "carbon_kg": 680.0, "risk_score": 38.0, "transport_mode": "sea"}),

    # Busan connections
    ("busan_port", "shanghai_port", {"cost_usd": 600.0, "time_hours": 36.0, "carbon_kg": 150.0, "risk_score": 10.0, "transport_mode": "sea"}),
    ("busan_port", "la_port", {"cost_usd": 3200.0, "time_hours": 264.0, "carbon_kg": 800.0, "risk_score": 32.0, "transport_mode": "sea"}),
    ("busan_port", "tokyo_port", {"cost_usd": 500.0, "time_hours": 24.0, "carbon_kg": 120.0, "risk_score": 8.0, "transport_mode": "sea"}),

    # Tokyo connections
    ("tokyo_port", "la_port", {"cost_usd": 3000.0, "time_hours": 240.0, "carbon_kg": 750.0, "risk_score": 30.0, "transport_mode": "sea"}),
    ("tokyo_port", "panama_customs", {"cost_usd": 3400.0, "time_hours": 312.0, "carbon_kg": 880.0, "risk_score": 42.0, "transport_mode": "sea"}),

    # Air freight alternatives (fast, expensive, moderate carbon)
    ("shanghai_port", "la_dc", {"cost_usd": 8500.0, "time_hours": 14.0, "carbon_kg": 2200.0, "risk_score": 8.0, "transport_mode": "air"}),
    ("shanghai_port", "rotterdam_dc", {"cost_usd": 7800.0, "time_hours": 12.0, "carbon_kg": 2000.0, "risk_score": 7.0, "transport_mode": "air"}),
    ("singapore_port", "london_dc", {"cost_usd": 7200.0, "time_hours": 13.0, "carbon_kg": 1900.0, "risk_score": 6.0, "transport_mode": "air"}),
    ("dubai_port", "ny_dc", {"cost_usd": 8000.0, "time_hours": 16.0, "carbon_kg": 2100.0, "risk_score": 9.0, "transport_mode": "air"}),
    ("tokyo_port", "ny_dc", {"cost_usd": 9000.0, "time_hours": 15.0, "carbon_kg": 2300.0, "risk_score": 10.0, "transport_mode": "air"}),

    # Chicago connections
    ("chicago_dc", "ny_dc", {"cost_usd": 650.0, "time_hours": 24.0, "carbon_kg": 95.0, "risk_score": 10.0, "transport_mode": "rail"}),
    ("chicago_dc", "la_dc", {"cost_usd": 800.0, "time_hours": 36.0, "carbon_kg": 120.0, "risk_score": 12.0, "transport_mode": "rail"}),

    # London connections
    ("london_dc", "rotterdam_dc", {"cost_usd": 450.0, "time_hours": 10.0, "carbon_kg": 55.0, "risk_score": 6.0, "transport_mode": "rail"}),
    ("london_dc", "hamburg_dc", {"cost_usd": 500.0, "time_hours": 14.0, "carbon_kg": 60.0, "risk_score": 7.0, "transport_mode": "rail"}),
]


# ── Helper functions ─────────────────────────────────────────────────


def _normalized_value(raw: float, min_val: float, max_val: float) -> float:
    """Min-max normalize a single value to [0.0, 1.0].

    Returns 0.0 when min equals max (all edges have the same value).
    """
    if max_val == min_val:
        return 0.0
    return (raw - min_val) / (max_val - min_val)


def _compute_metric_ranges(graph: nx.DiGraph) -> dict[str, tuple[float, float]]:
    """Compute (min, max) for each metric across all edges in the graph."""
    metrics = ["cost_usd", "time_hours", "carbon_kg", "risk_score"]
    ranges: dict[str, tuple[float, float]] = {}
    for metric in metrics:
        values = [graph[u][v][metric] for u, v in graph.edges()]
        ranges[metric] = (min(values), max(values))
    return ranges


# ── OptimizationEngine ───────────────────────────────────────────────


class OptimizationEngine:
    """Computes optimal supply chain routes using weighted graph scoring.

    The logistics network is modelled as a directed graph where nodes are
    logistics hubs (ports, warehouses, distribution centres, customs) and
    edges carry cost, time, carbon, and risk attributes.

    Route scoring normalises all edge metrics to [0, 1] via min-max
    normalization, then computes a composite score using user-supplied
    weights.  The top 3 routes are returned, each labelled with its
    dominant optimisation dimension.
    """

    def __init__(self) -> None:
        """Initialise the graph with the default logistics network."""
        self._graph = nx.DiGraph()
        self._build_default_graph()
        self._metric_ranges = _compute_metric_ranges(self._graph)

    # ── Graph construction ───────────────────────────────────────────

    def _build_default_graph(self) -> None:
        """Populate the graph with the default set of nodes and edges."""
        for node in _NODES:
            self._graph.add_node(node["id"], **node)
        for src, dst, attrs in _EDGES:
            self._graph.add_edge(src, dst, **attrs)

    @property
    def graph(self) -> nx.DiGraph:
        """Expose the underlying graph (read-only access for tests)."""
        return self._graph

    # ── Route computation ────────────────────────────────────────────

    def compute_routes(
        self,
        origin: str,
        destination: str,
        weights: OptimizationWeights,
    ) -> list[RouteOption]:
        """Compute the top 3 routes between *origin* and *destination*.

        Steps:
        1. Enumerate all simple paths up to 6 hops.
        2. Score each path using normalised, weighted metrics.
        3. Sort by ascending composite score and pick the top 3.
        4. Label each route (cheapest / fastest / greenest / safest).
        5. Mark the best composite-score route as recommended.

        Returns an empty list when no path exists.
        """
        if origin not in self._graph or destination not in self._graph:
            return []
        if origin == destination:
            return []

        # Discover all simple paths (cutoff=6 keeps it fast — Req 12.5)
        all_paths = list(
            nx.all_simple_paths(self._graph, origin, destination, cutoff=6)
        )
        if not all_paths:
            return []

        # Score every path
        scored: list[dict] = []
        for path in all_paths:
            metrics = self._score_path(path)
            composite = (
                weights.cost * metrics["norm_cost_sum"]
                + weights.time * metrics["norm_time_sum"]
                + weights.carbon * metrics["norm_carbon_sum"]
                + weights.risk * metrics["norm_risk_max"]
            )
            scored.append({
                "path": path,
                "composite": composite,
                **metrics,
            })

        # Sort by composite score (ascending = better)
        scored.sort(key=lambda s: s["composite"])

        # Take top 3
        top = scored[:3]

        # Label routes by single-metric rankings across the top set
        self._label_routes(top)

        # Build RouteOption models
        results: list[RouteOption] = []
        for i, entry in enumerate(top):
            results.append(
                RouteOption(
                    route_id=str(uuid.uuid4()),
                    waypoints=entry["path"],
                    label=entry["label"],
                    cost_usd=entry["raw_cost_sum"],
                    eta_hours=entry["raw_time_sum"],
                    carbon_kg=entry["raw_carbon_sum"],
                    risk_score=entry["raw_risk_max"],
                    score=round(entry["composite"], 6),
                    is_recommended=(i == 0),
                )
            )

        return results

    # ── Internal scoring helpers ─────────────────────────────────────

    def _score_path(self, path: list[str]) -> dict:
        """Compute raw and normalised metrics for a single path."""
        ranges = self._metric_ranges

        raw_cost = 0.0
        raw_time = 0.0
        raw_carbon = 0.0
        raw_risk = 0.0

        norm_cost = 0.0
        norm_time = 0.0
        norm_carbon = 0.0
        norm_risk = 0.0

        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            edge = self._graph[u][v]

            raw_cost += edge["cost_usd"]
            raw_time += edge["time_hours"]
            raw_carbon += edge["carbon_kg"]

            edge_risk = edge["risk_score"]
            raw_risk = max(raw_risk, edge_risk)

            norm_cost += _normalized_value(
                edge["cost_usd"], *ranges["cost_usd"]
            )
            norm_time += _normalized_value(
                edge["time_hours"], *ranges["time_hours"]
            )
            norm_carbon += _normalized_value(
                edge["carbon_kg"], *ranges["carbon_kg"]
            )
            norm_risk = max(
                norm_risk,
                _normalized_value(edge_risk, *ranges["risk_score"]),
            )

        return {
            "raw_cost_sum": raw_cost,
            "raw_time_sum": raw_time,
            "raw_carbon_sum": raw_carbon,
            "raw_risk_max": raw_risk,
            "norm_cost_sum": norm_cost,
            "norm_time_sum": norm_time,
            "norm_carbon_sum": norm_carbon,
            "norm_risk_max": norm_risk,
        }

    @staticmethod
    def _label_routes(top: list[dict]) -> None:
        """Assign a label to each route based on its dominant metric.

        Labels: cheapest, fastest, greenest, safest.
        If a route wins multiple categories, the first match wins and
        subsequent routes get the next-best label.
        """
        if not top:
            return

        # Determine single-metric winners
        metrics = [
            ("cheapest", "norm_cost_sum", False),   # lowest sum
            ("fastest", "norm_time_sum", False),     # lowest sum
            ("greenest", "norm_carbon_sum", False),  # lowest sum
            ("safest", "norm_risk_max", False),      # lowest max
        ]

        assigned_labels: dict[int, str] = {}
        used_labels: set[str] = set()

        for label, key, _ in metrics:
            # Find the route with the best (lowest) value for this metric
            # that hasn't already been labelled
            best_idx = None
            best_val = float("inf")
            for i, entry in enumerate(top):
                if i in assigned_labels:
                    continue
                if entry[key] < best_val:
                    best_val = entry[key]
                    best_idx = i
            if best_idx is not None and label not in used_labels:
                assigned_labels[best_idx] = label
                used_labels.add(label)

        # Any remaining unlabelled routes get the first unused label
        remaining_labels = [
            lbl for lbl, _, _ in metrics if lbl not in used_labels
        ]
        for i in range(len(top)):
            if i not in assigned_labels:
                if remaining_labels:
                    assigned_labels[i] = remaining_labels.pop(0)
                else:
                    # Fallback: label by composite ranking
                    assigned_labels[i] = "cheapest"

        for i, entry in enumerate(top):
            entry["label"] = assigned_labels[i]

    # ── Graph rebuild ────────────────────────────────────────────────

    def rebuild_graph(self, settings: Settings) -> None:
        """Rebuild the graph incorporating updated settings.

        Currently re-initialises the default graph and recomputes metric
        ranges.  Future versions may adjust edge weights based on SLA
        thresholds and penalty values from *settings*.
        """
        self._graph.clear()
        self._build_default_graph()
        self._metric_ranges = _compute_metric_ranges(self._graph)
