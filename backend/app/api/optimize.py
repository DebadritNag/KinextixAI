"""Route optimization API endpoint.

Requirements: 15.1, 15.2
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.models.api import OptimizeRequest
from app.services.data_store import data_store
from app.services.optimization_engine import OptimizationEngine

router = APIRouter(prefix="/api/optimize", tags=["optimize"])

# Module-level singleton
_engine = OptimizationEngine()

# ---------------------------------------------------------------------------
# Name → graph node ID mapping
# ---------------------------------------------------------------------------
# Shipment origin/destination strings use full human-readable names.
# The graph uses short IDs. This table maps every known full name to its ID.

_NAME_TO_NODE: dict[str, str] = {
    # Ports
    "shanghai port":                "shanghai_port",
    "singapore port":               "singapore_port",
    "dubai port":                   "dubai_port",
    "rotterdam port":               "rotterdam_port",
    "hamburg port":                 "hamburg_port",
    "los angeles port":             "la_port",
    "new york port":                "ny_port",
    "busan port":                   "busan_port",
    "mumbai port":                  "mumbai_port",
    "shenzhen port":                "shenzhen_port",
    "tokyo port":                   "tokyo_port",
    # Warehouses
    "shanghai warehouse":           "shanghai_wh",
    "singapore warehouse":          "singapore_wh",
    "dubai warehouse":              "dubai_wh",
    # Distribution centres
    "rotterdam distribution center":"rotterdam_dc",
    "hamburg distribution center":  "hamburg_dc",
    "los angeles distribution center": "la_dc",
    "new york distribution center": "ny_dc",
    "chicago distribution center":  "chicago_dc",
    "london distribution center":   "london_dc",
    # Customs
    "suez canal customs":           "suez_customs",
    "panama canal customs":         "panama_customs",
}


def _to_node_id(name: str) -> str:
    """Convert a human-readable location name to a graph node ID.

    Tries the lookup table first, then falls back to the simple
    lowercase + underscore heuristic for any names not in the table.
    """
    key = name.strip().lower()
    if key in _NAME_TO_NODE:
        return _NAME_TO_NODE[key]
    # Fallback: simple normalisation (handles exact graph IDs passed directly)
    return key.replace(" ", "_")


def _envelope(data: object) -> dict:
    return {
        "status": "success",
        "data": data,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("")
async def optimize_route(request: OptimizeRequest):
    """Compute optimal routes for a shipment."""
    shipment = data_store.get_shipment(request.shipment_id)
    if shipment is None:
        raise HTTPException(
            status_code=404,
            detail=f"Shipment {request.shipment_id} not found",
        )

    origin      = _to_node_id(shipment.origin)
    destination = _to_node_id(shipment.destination)

    start = time.perf_counter()
    routes = _engine.compute_routes(origin, destination, request.weights)
    elapsed_ms = (time.perf_counter() - start) * 1000

    return _envelope({
        "routes": [r.model_dump(mode="json") for r in routes],
        "computation_time_ms": round(elapsed_ms, 2),
    })
