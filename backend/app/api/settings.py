"""Settings API endpoints.

Requirements: 15.1, 15.2
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.models.settings import Settings
from app.services.data_store import data_store

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _envelope(data: object) -> dict:
    """Wrap response data in the standard ApiEnvelope format."""
    return {
        "status": "success",
        "data": data,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("")
async def get_settings():
    """Return the current application settings."""
    settings = data_store.get_settings()
    return _envelope(settings.model_dump(mode="json"))


@router.put("")
async def update_settings(settings: Settings):
    """Update application settings."""
    data_store.update_settings(settings)
    updated = data_store.get_settings()
    return _envelope(updated.model_dump(mode="json"))
