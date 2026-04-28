"""Shipment-related Pydantic data models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ShipmentStatus(str, Enum):
    """Possible statuses for a shipment."""

    CREATED = "created"
    IN_TRANSIT = "in_transit"
    DELAYED = "delayed"
    DELIVERED = "delivered"
    DISRUPTED = "disrupted"


class Coordinates(BaseModel):
    """Geographic coordinates with latitude/longitude constraints."""

    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class TimelineEvent(BaseModel):
    """A single event in a shipment's timeline."""

    timestamp: datetime
    event: str
    location: Optional[str] = None
    details: Optional[str] = None


class Shipment(BaseModel):
    """Core shipment model tracking a logistics unit from origin to destination."""

    id: str
    origin: str
    destination: str
    origin_coords: Coordinates
    destination_coords: Coordinates
    current_coords: Coordinates
    status: ShipmentStatus
    created_at: datetime
    updated_at: datetime
    eta_predicted: Optional[datetime] = None
    eta_confidence_low: Optional[datetime] = None
    eta_confidence_high: Optional[datetime] = None
    delay_minutes: int = 0
    weather_condition: str = "clear"
    route_id: Optional[str] = None
    timeline: list[TimelineEvent] = []
