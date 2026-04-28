"""Analytics Pydantic data models."""

from pydantic import BaseModel


class AnalyticsData(BaseModel):
    """Aggregate analytics data for the analytics page."""

    delay_trends: list[dict]
    cost_savings: list[dict]
    carbon_reduction: list[dict]
    sla_compliance_pct: float
    sla_trend: list[dict]
