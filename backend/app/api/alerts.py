"""Risk alerts API endpoints.

Requirements: 15.1, 15.2
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.services.data_store import data_store

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _envelope(data: object) -> dict:
    """Wrap response data in the standard ApiEnvelope format."""
    return {
        "status": "success",
        "data": data,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("")
async def list_alerts():
    """Return all active risk alerts."""
    alerts = data_store.get_alerts()
    return _envelope([a.model_dump(mode="json") for a in alerts])
