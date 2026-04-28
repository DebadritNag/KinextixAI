"""API request/response Pydantic data models."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.models.optimization import OptimizationWeights, RouteOption


class OptimizeRequest(BaseModel):
    """Request body for the route optimization endpoint."""

    shipment_id: str
    weights: OptimizationWeights


class OptimizeResponse(BaseModel):
    """Response body for the route optimization endpoint."""

    routes: list[RouteOption]
    computation_time_ms: float


class ExplainRequest(BaseModel):
    """Request body for the route explanation endpoint."""

    route: RouteOption
    alternatives: list[RouteOption]


class ExplainResponse(BaseModel):
    """Response body for the route explanation endpoint."""

    explanation: str
    source: str  # "model" or "fallback"


class LoginRequest(BaseModel):
    """Request body for the mock login endpoint."""

    username: str
    password: str


class AuthResponse(BaseModel):
    """Response body for authentication endpoints."""

    token: str
    user: dict


class StatusResponse(BaseModel):
    """Simple status message response."""

    message: str


class ApiEnvelope(BaseModel):
    """Standard API response wrapper with consistent schema."""

    status: str  # "success" or "error"
    data: Optional[Any] = None
    error: Optional[dict] = None
    timestamp: datetime
