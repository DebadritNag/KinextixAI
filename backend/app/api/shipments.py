"""Shipment API endpoints.

Requirements: 15.1, 15.2
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.services.data_store import data_store

router = APIRouter(prefix="/api/shipments", tags=["shipments"])


def _envelope(data: object) -> dict:
    """Wrap response data in the standard ApiEnvelope format."""
    return {
        "status": "success",
        "data": data,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("")
async def list_shipments():
    """Return all active shipments."""
    shipments = data_store.get_shipments()
    return _envelope([s.model_dump(mode="json") for s in shipments])


@router.get("/{shipment_id}")
async def get_shipment(shipment_id: str):
    """Return a single shipment with its timeline."""
    shipment = data_store.get_shipment(shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
    return _envelope(shipment.model_dump(mode="json"))
