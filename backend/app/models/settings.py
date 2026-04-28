"""Application settings Pydantic data models."""

from pydantic import BaseModel

from app.models.optimization import OptimizationWeights


class Settings(BaseModel):
    """System configuration for SLA thresholds, penalties, and default weights."""

    sla_thresholds: dict[str, float]  # category -> hours
    penalties: dict[str, float]  # category -> USD
    default_weights: OptimizationWeights
