"""Optimization-related Pydantic data models."""

from pydantic import BaseModel, Field


class OptimizationWeights(BaseModel):
    """User-configurable weights for route optimization scoring.

    Each weight must be between 0.0 and 1.0 inclusive.
    """

    cost: float = Field(ge=0.0, le=1.0, default=0.25)
    time: float = Field(ge=0.0, le=1.0, default=0.25)
    carbon: float = Field(ge=0.0, le=1.0, default=0.25)
    risk: float = Field(ge=0.0, le=1.0, default=0.25)


class RouteOption(BaseModel):
    """A single route option returned by the optimization engine."""

    route_id: str
    waypoints: list[str]
    label: str  # "cheapest", "fastest", "greenest", "safest"
    cost_usd: float
    eta_hours: float
    carbon_kg: float
    risk_score: float = Field(ge=0, le=100)
    score: float  # Composite weighted score
    is_recommended: bool = False
