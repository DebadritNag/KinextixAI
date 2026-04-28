"""Demo mode API endpoint.

Requirements: 10.6, 15.1
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.data_store import data_store
from app.services.disruption_detector import DisruptionDetector

router = APIRouter(prefix="/api/demo", tags=["demo"])

# Module-level singleton
_detector = DisruptionDetector()


def _envelope(data: object) -> dict:
    """Wrap response data in the standard ApiEnvelope format."""
    return {
        "status": "success",
        "data": data,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class TriggerDisruptionRequest(BaseModel):
    """Request body for the trigger-disruption endpoint."""

    shipment_id: str


@router.post("/trigger-disruption")
async def trigger_disruption(request: TriggerDisruptionRequest):
    """Force a high-severity disruption on a specific shipment.

    Modifies the shipment to exhibit anomalous behaviour (severe weather,
    large delay, off-route coordinates) then runs the disruption detector
    to generate a HIGH severity alert.
    """
    shipment = data_store.get_shipment(request.shipment_id)
    if shipment is None:
        raise HTTPException(
            status_code=404,
            detail=f"Shipment {request.shipment_id} not found",
        )

    # Mutate the shipment to trigger a high-severity anomaly
    modified = shipment.model_copy(
        update={
            "weather_condition": "severe",
            "delay_minutes": shipment.delay_minutes + 120,
            # Shift current coords ~50 km off route
            "current_coords": shipment.current_coords.model_copy(
                update={
                    "lat": min(90.0, shipment.current_coords.lat + 0.45),
                    "lng": min(180.0, shipment.current_coords.lng + 0.45),
                }
            ),
        }
    )
    data_store.upsert_shipment(modified)

    # Run disruption detection on the modified shipment
    alert = _detector.analyze(modified)

    if alert is None:
        # Force-create a HIGH alert if the model didn't flag it
        from uuid import uuid4
        from app.models.alert import RiskAlert, Severity

        alert = RiskAlert(
            id=str(uuid4()),
            shipment_id=modified.id,
            severity=Severity.HIGH,
            title="HIGH disruption risk detected",
            description=(
                f"Shipment {modified.id} from {modified.origin} to "
                f"{modified.destination} has been manually triggered for "
                f"disruption demo. Weather: {modified.weather_condition}, "
                f"delay: {modified.delay_minutes}min."
            ),
            created_at=datetime.now(timezone.utc),
            is_active=True,
        )

    data_store.add_alert(alert)
    return _envelope(alert.model_dump(mode="json"))
