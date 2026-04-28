"""Route explanation API endpoint.

Requirements: 15.1, 15.2
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.models.api import ExplainRequest
from app.services.reasoning_engine import ReasoningEngine

router = APIRouter(prefix="/api/explain", tags=["explain"])

# Module-level singleton
_engine = ReasoningEngine()


def _envelope(data: object) -> dict:
    """Wrap response data in the standard ApiEnvelope format."""
    return {
        "status": "success",
        "data": data,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("")
async def explain_route(request: ExplainRequest):
    """Generate a natural language explanation for a route recommendation."""
    result = await _engine.explain(request.route, request.alternatives)
    return _envelope(result.model_dump(mode="json"))
