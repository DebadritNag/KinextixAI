"""Unit tests for the OptimizationEngine service.

Validates graph construction, min-max normalization, route scoring,
labelling, performance, and rebuild behaviour.

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7
"""

import time

import pytest

from app.models import OptimizationWeights, RouteOption, Settings
from app.services.optimization_engine import (
    OptimizationEngine,
    _compute_metric_ranges,
    _normalized_value,
)


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def engine() -> OptimizationEngine:
    """Return a freshly initialised OptimizationEngine."""
    return OptimizationEngine()


@pytest.fixture
def equal_weights() -> OptimizationWeights:
    """Return equal weights (0.25 each)."""
    return OptimizationWeights(cost=0.25, time=0.25, carbon=0.25, risk=0.25)


# ── Normalization helper tests ───────────────────────────────────────


class TestNormalizedValue:
    def test_min_returns_zero(self) -> None:
        assert _normalized_value(10.0, 10.0, 100.0) == 0.0

    def test_max_returns_one(self) -> None:
        assert _normalized_value(100.0, 10.0, 100.0) == 1.0

    def test_midpoint(self) -> None:
        assert _normalized_value(55.0, 10.0, 100.0) == pytest.approx(0.5)

    def test_equal_min_max_returns_zero(self) -> None:
        """When all edges have the same value, normalization returns 0.0."""
        assert _normalized_value(42.0, 42.0, 42.0) == 0.0

    def test_result_in_range(self) -> None:
        result = _normalized_value(50.0, 0.0, 200.0)
        assert 0.0 <= result <= 1.0


# ── Graph construction tests (Req 12.1, 12.6) ───────────────────────


class TestGraphConstruction:
    def test_minimum_node_count(self, engine: OptimizationEngine) -> None:
        """Graph must have at least 20 nodes (Req 12.6)."""
        assert engine.graph.number_of_nodes() >= 20

    def test_minimum_edge_count(self, engine: OptimizationEngine) -> None:
        """Graph must have at least 50 edges (Req 12.6)."""
        assert engine.graph.number_of_edges() >= 50

    def test_graph_is_directed(self, engine: OptimizationEngine) -> None:
        """Graph must be a directed graph (Req 12.1)."""
        assert engine.graph.is_directed()

    def test_node_types_present(self, engine: OptimizationEngine) -> None:
        """Graph should contain ports, warehouses, distribution centers, and customs."""
        types = {engine.graph.nodes[n]["type"] for n in engine.graph.nodes()}
        assert "port" in types
        assert "warehouse" in types
        assert "distribution_center" in types
        assert "customs" in types

    def test_node_has_required_attributes(self, engine: OptimizationEngine) -> None:
        """Each node must have id, name, type, and coords."""
        for node_id in engine.graph.nodes():
            data = engine.graph.nodes[node_id]
            assert "id" in data
            assert "name" in data
            assert "type" in data
            assert "coords" in data
            assert "lat" in data["coords"]
            assert "lng" in data["coords"]

    def test_transport_modes_present(self, engine: OptimizationEngine) -> None:
        """Graph should contain sea, air, rail, and road transport modes."""
        modes = {engine.graph[u][v]["transport_mode"] for u, v in engine.graph.edges()}
        assert "sea" in modes
        assert "air" in modes
        assert "rail" in modes
        assert "road" in modes


# ── Edge attribute tests (Req 12.2) ─────────────────────────────────


class TestEdgeAttributes:
    def test_edges_have_required_metrics(self, engine: OptimizationEngine) -> None:
        """Each edge must carry cost_usd, time_hours, carbon_kg, risk_score, transport_mode."""
        for u, v in engine.graph.edges():
            edge = engine.graph[u][v]
            assert "cost_usd" in edge
            assert "time_hours" in edge
            assert "carbon_kg" in edge
            assert "risk_score" in edge
            assert "transport_mode" in edge

    def test_risk_scores_in_range(self, engine: OptimizationEngine) -> None:
        """Risk scores must be between 0 and 100."""
        for u, v in engine.graph.edges():
            risk = engine.graph[u][v]["risk_score"]
            assert 0.0 <= risk <= 100.0

    def test_positive_costs(self, engine: OptimizationEngine) -> None:
        """All costs must be positive."""
        for u, v in engine.graph.edges():
            assert engine.graph[u][v]["cost_usd"] > 0

    def test_positive_times(self, engine: OptimizationEngine) -> None:
        """All times must be positive."""
        for u, v in engine.graph.edges():
            assert engine.graph[u][v]["time_hours"] > 0

    def test_positive_carbon(self, engine: OptimizationEngine) -> None:
        """All carbon values must be positive."""
        for u, v in engine.graph.edges():
            assert engine.graph[u][v]["carbon_kg"] > 0


# ── Metric ranges / normalization tests (Req 12.7) ──────────────────


class TestMetricRanges:
    def test_ranges_computed_for_all_metrics(self, engine: OptimizationEngine) -> None:
        ranges = _compute_metric_ranges(engine.graph)
        assert "cost_usd" in ranges
        assert "time_hours" in ranges
        assert "carbon_kg" in ranges
        assert "risk_score" in ranges

    def test_min_less_than_or_equal_max(self, engine: OptimizationEngine) -> None:
        ranges = _compute_metric_ranges(engine.graph)
        for metric, (lo, hi) in ranges.items():
            assert lo <= hi, f"{metric}: min {lo} > max {hi}"


# ── Route computation tests (Req 12.3, 12.4) ────────────────────────


class TestComputeRoutes:
    def test_returns_up_to_three_routes(
        self, engine: OptimizationEngine, equal_weights: OptimizationWeights
    ) -> None:
        """Must return at most 3 routes (Req 12.4)."""
        routes = engine.compute_routes("shanghai_port", "ny_dc", equal_weights)
        assert 1 <= len(routes) <= 3

    def test_routes_sorted_by_score(
        self, engine: OptimizationEngine, equal_weights: OptimizationWeights
    ) -> None:
        """Routes must be sorted by ascending composite score."""
        routes = engine.compute_routes("shanghai_port", "ny_dc", equal_weights)
        scores = [r.score for r in routes]
        assert scores == sorted(scores)

    def test_first_route_is_recommended(
        self, engine: OptimizationEngine, equal_weights: OptimizationWeights
    ) -> None:
        """The top-scoring route must be marked as recommended."""
        routes = engine.compute_routes("shanghai_port", "ny_dc", equal_weights)
        assert routes[0].is_recommended is True

    def test_only_one_recommended(
        self, engine: OptimizationEngine, equal_weights: OptimizationWeights
    ) -> None:
        """Exactly one route should be recommended."""
        routes = engine.compute_routes("shanghai_port", "ny_dc", equal_weights)
        recommended = [r for r in routes if r.is_recommended]
        assert len(recommended) == 1

    def test_routes_have_valid_labels(
        self, engine: OptimizationEngine, equal_weights: OptimizationWeights
    ) -> None:
        """Each route must have a valid label."""
        valid_labels = {"cheapest", "fastest", "greenest", "safest"}
        routes = engine.compute_routes("shanghai_port", "ny_dc", equal_weights)
        for route in routes:
            assert route.label in valid_labels

    def test_routes_have_unique_labels(
        self, engine: OptimizationEngine, equal_weights: OptimizationWeights
    ) -> None:
        """Each route in the top 3 should have a distinct label."""
        routes = engine.compute_routes("shanghai_port", "ny_dc", equal_weights)
        labels = [r.label for r in routes]
        assert len(labels) == len(set(labels))

    def test_route_waypoints_start_at_origin(
        self, engine: OptimizationEngine, equal_weights: OptimizationWeights
    ) -> None:
        routes = engine.compute_routes("shanghai_port", "ny_dc", equal_weights)
        for route in routes:
            assert route.waypoints[0] == "shanghai_port"

    def test_route_waypoints_end_at_destination(
        self, engine: OptimizationEngine, equal_weights: OptimizationWeights
    ) -> None:
        routes = engine.compute_routes("shanghai_port", "ny_dc", equal_weights)
        for route in routes:
            assert route.waypoints[-1] == "ny_dc"

    def test_route_has_positive_metrics(
        self, engine: OptimizationEngine, equal_weights: OptimizationWeights
    ) -> None:
        routes = engine.compute_routes("shanghai_port", "ny_dc", equal_weights)
        for route in routes:
            assert route.cost_usd > 0
            assert route.eta_hours > 0
            assert route.carbon_kg > 0
            assert route.risk_score >= 0

    def test_route_option_model_fields(
        self, engine: OptimizationEngine, equal_weights: OptimizationWeights
    ) -> None:
        """Each route must be a valid RouteOption model."""
        routes = engine.compute_routes("shanghai_port", "ny_dc", equal_weights)
        for route in routes:
            assert isinstance(route, RouteOption)
            assert isinstance(route.route_id, str)
            assert len(route.route_id) > 0

    def test_nonexistent_origin_returns_empty(
        self, engine: OptimizationEngine, equal_weights: OptimizationWeights
    ) -> None:
        routes = engine.compute_routes("nonexistent", "ny_dc", equal_weights)
        assert routes == []

    def test_nonexistent_destination_returns_empty(
        self, engine: OptimizationEngine, equal_weights: OptimizationWeights
    ) -> None:
        routes = engine.compute_routes("shanghai_port", "nonexistent", equal_weights)
        assert routes == []

    def test_no_path_returns_empty(
        self, engine: OptimizationEngine, equal_weights: OptimizationWeights
    ) -> None:
        """When no path exists between two nodes, return empty list."""
        # ny_dc has no outgoing edges to shanghai_port via simple paths
        # that don't loop, so this may or may not return results depending
        # on graph connectivity. Test with a truly disconnected node.
        engine.graph.add_node("isolated_node", id="isolated_node", name="Isolated", type="port", coords={"lat": 0, "lng": 0})
        routes = engine.compute_routes("isolated_node", "ny_dc", equal_weights)
        assert routes == []
        engine.graph.remove_node("isolated_node")


# ── Weight sensitivity tests (Req 12.3) ─────────────────────────────


class TestWeightSensitivity:
    def test_cost_weight_favours_cheaper_routes(
        self, engine: OptimizationEngine
    ) -> None:
        """When cost weight is dominant, the recommended route should be cheapest."""
        cost_weights = OptimizationWeights(cost=1.0, time=0.0, carbon=0.0, risk=0.0)
        routes = engine.compute_routes("shanghai_port", "ny_dc", cost_weights)
        if len(routes) >= 2:
            assert routes[0].cost_usd <= routes[1].cost_usd

    def test_time_weight_favours_faster_routes(
        self, engine: OptimizationEngine
    ) -> None:
        """When time weight is dominant, the recommended route should be fastest."""
        time_weights = OptimizationWeights(cost=0.0, time=1.0, carbon=0.0, risk=0.0)
        routes = engine.compute_routes("shanghai_port", "ny_dc", time_weights)
        if len(routes) >= 2:
            assert routes[0].eta_hours <= routes[1].eta_hours

    def test_carbon_weight_favours_greener_routes(
        self, engine: OptimizationEngine
    ) -> None:
        """When carbon weight is dominant, the recommended route should be greenest."""
        carbon_weights = OptimizationWeights(cost=0.0, time=0.0, carbon=1.0, risk=0.0)
        routes = engine.compute_routes("shanghai_port", "ny_dc", carbon_weights)
        if len(routes) >= 2:
            assert routes[0].carbon_kg <= routes[1].carbon_kg

    def test_risk_weight_favours_safer_routes(
        self, engine: OptimizationEngine
    ) -> None:
        """When risk weight is dominant, the recommended route should be safest."""
        risk_weights = OptimizationWeights(cost=0.0, time=0.0, carbon=0.0, risk=1.0)
        routes = engine.compute_routes("shanghai_port", "ny_dc", risk_weights)
        if len(routes) >= 2:
            assert routes[0].risk_score <= routes[1].risk_score


# ── Scoring formula tests (Req 12.3) ────────────────────────────────


class TestScoringFormula:
    def test_risk_uses_max_not_sum(self, engine: OptimizationEngine) -> None:
        """Risk metric should use max (worst-case) across edges, not sum."""
        weights = OptimizationWeights(cost=0.0, time=0.0, carbon=0.0, risk=1.0)
        routes = engine.compute_routes("shanghai_port", "ny_dc", weights)
        for route in routes:
            # The risk_score on the route is the raw max risk across edges
            edge_risks = []
            for i in range(len(route.waypoints) - 1):
                u, v = route.waypoints[i], route.waypoints[i + 1]
                edge_risks.append(engine.graph[u][v]["risk_score"])
            assert route.risk_score == max(edge_risks)

    def test_cost_is_sum_of_edges(self, engine: OptimizationEngine) -> None:
        """Cost metric should be the sum of all edge costs."""
        weights = OptimizationWeights()
        routes = engine.compute_routes("shanghai_port", "la_dc", weights)
        for route in routes:
            expected_cost = sum(
                engine.graph[route.waypoints[i]][route.waypoints[i + 1]]["cost_usd"]
                for i in range(len(route.waypoints) - 1)
            )
            assert route.cost_usd == pytest.approx(expected_cost)


# ── Performance tests (Req 12.5) ────────────────────────────────────


class TestPerformance:
    def test_compute_routes_within_three_seconds(
        self, engine: OptimizationEngine, equal_weights: OptimizationWeights
    ) -> None:
        """Route computation must complete within 3 seconds (Req 12.5)."""
        start = time.monotonic()
        engine.compute_routes("shanghai_port", "ny_dc", equal_weights)
        elapsed = time.monotonic() - start
        assert elapsed < 3.0

    def test_multiple_computations_within_three_seconds(
        self, engine: OptimizationEngine, equal_weights: OptimizationWeights
    ) -> None:
        """Even repeated computations should stay well under 3 seconds each."""
        for _ in range(10):
            start = time.monotonic()
            engine.compute_routes("shanghai_port", "ny_dc", equal_weights)
            elapsed = time.monotonic() - start
            assert elapsed < 3.0


# ── Rebuild graph tests ──────────────────────────────────────────────


class TestRebuildGraph:
    def test_rebuild_preserves_node_count(self, engine: OptimizationEngine) -> None:
        """After rebuild, graph should still have >= 20 nodes."""
        settings = Settings(
            sla_thresholds={"standard": 72.0, "express": 24.0},
            penalties={"standard": 50.0, "express": 150.0},
            default_weights=OptimizationWeights(),
        )
        engine.rebuild_graph(settings)
        assert engine.graph.number_of_nodes() >= 20

    def test_rebuild_preserves_edge_count(self, engine: OptimizationEngine) -> None:
        """After rebuild, graph should still have >= 50 edges."""
        settings = Settings(
            sla_thresholds={"standard": 72.0},
            penalties={"standard": 50.0},
            default_weights=OptimizationWeights(),
        )
        engine.rebuild_graph(settings)
        assert engine.graph.number_of_edges() >= 50

    def test_routes_work_after_rebuild(self, engine: OptimizationEngine) -> None:
        """Route computation should work after a graph rebuild."""
        settings = Settings(
            sla_thresholds={"standard": 72.0},
            penalties={"standard": 50.0},
            default_weights=OptimizationWeights(),
        )
        engine.rebuild_graph(settings)
        routes = engine.compute_routes(
            "shanghai_port", "ny_dc", OptimizationWeights()
        )
        assert len(routes) >= 1


# ── Edge case tests ──────────────────────────────────────────────────


class TestEdgeCases:
    def test_same_origin_and_destination(
        self, engine: OptimizationEngine, equal_weights: OptimizationWeights
    ) -> None:
        """Same origin and destination should return empty (no self-loops)."""
        routes = engine.compute_routes("shanghai_port", "shanghai_port", equal_weights)
        assert routes == []

    def test_adjacent_nodes(
        self, engine: OptimizationEngine, equal_weights: OptimizationWeights
    ) -> None:
        """Direct neighbours should return at least one route."""
        routes = engine.compute_routes("shanghai_port", "shanghai_wh", equal_weights)
        assert len(routes) >= 1
        # Direct route should have exactly 2 waypoints
        assert len(routes[0].waypoints) == 2

    def test_fewer_than_three_paths_returns_all(
        self, engine: OptimizationEngine, equal_weights: OptimizationWeights
    ) -> None:
        """When fewer than 3 paths exist, return all available."""
        routes = engine.compute_routes("shanghai_port", "shanghai_wh", equal_weights)
        # There should be exactly 1 direct path
        assert 1 <= len(routes) <= 3
