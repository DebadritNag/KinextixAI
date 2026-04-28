"""Pydantic data models for the Kinetix AI backend."""

from app.models.alert import RiskAlert, Severity
from app.models.analytics import AnalyticsData
from app.models.api import (
    ApiEnvelope,
    AuthResponse,
    ExplainRequest,
    ExplainResponse,
    LoginRequest,
    OptimizeRequest,
    OptimizeResponse,
    StatusResponse,
)
from app.models.optimization import OptimizationWeights, RouteOption
from app.models.prediction import ETAPrediction
from app.models.settings import Settings
from app.models.shipment import (
    Coordinates,
    Shipment,
    ShipmentStatus,
    TimelineEvent,
)

__all__ = [
    # Shipment models
    "Coordinates",
    "Shipment",
    "ShipmentStatus",
    "TimelineEvent",
    # Alert models
    "RiskAlert",
    "Severity",
    # Optimization models
    "OptimizationWeights",
    "RouteOption",
    # Prediction models
    "ETAPrediction",
    # Settings models
    "Settings",
    # Analytics models
    "AnalyticsData",
    # API models
    "ApiEnvelope",
    "AuthResponse",
    "ExplainRequest",
    "ExplainResponse",
    "LoginRequest",
    "OptimizeRequest",
    "OptimizeResponse",
    "StatusResponse",
]
