"""Analytics API endpoint.

Requirements: 15.1, 15.2
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app.services.data_store import data_store

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _envelope(data: object) -> dict:
    """Wrap response data in the standard ApiEnvelope format."""
    return {
        "status": "success",
        "data": data,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("")
async def get_analytics(time_range: str = Query(default="24h")):
    """Return aggregate analytics data filtered by time range."""
    analytics = data_store.get_analytics(time_range)
    return _envelope(analytics.model_dump(mode="json"))
