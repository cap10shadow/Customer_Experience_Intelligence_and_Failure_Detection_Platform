from typing import Dict, List

from pydantic import BaseModel


class VolumeTrendPointDTO(BaseModel):
    date: str
    count: int


class CategoryTrendPointDTO(BaseModel):
    category: str
    count: int


class RegionTrendPointDTO(BaseModel):
    region: str
    count: int


class SentimentTrendPointDTO(BaseModel):
    date: str
    averageScore: float
    labelCounts: Dict[str, int]


class UrgencyTrendPointDTO(BaseModel):
    urgency: str
    count: int


class AnalyticsResponse(BaseModel):
    """
    Public Gateway DTO for GET /api/v1/analytics/trends -- a single-service
    read from anomaly_service's real `/api/v1/trends` summary capability
    (Batch 4A SS11/SS12, Part 5's backend capability audit). Every field
    here maps 1:1 to a real anomaly_service field; the Gateway performs no
    trend calculation, no clustering, no narrative generation, and no
    business interpretation -- only DTO transformation (snake_case ->
    camelCase, `category`/`urgency`/`region` enum values passed through
    as-is).

    Deliberately has no `patterns`, `organizationalInsights`,
    `strategicOpportunities`, or `recommendationEffectiveness` field:
    Part 5's backend capability audit confirmed none of those concepts
    exist anywhere in the backend today (no route, service, or module
    produces them). Representing them here -- even as an empty list --
    would misrepresent an unimplemented capability as a modeled-but-empty
    one; the frozen "no fake API fields" rule (Batch 1 SS24) forbids that.
    Those sections remain purely frontend-illustrative/future-capability
    presentation until a genuine backend capability exists for them.
    """

    period: str
    volumeTrend: List[VolumeTrendPointDTO]
    categoryTrend: List[CategoryTrendPointDTO]
    regionTrend: List[RegionTrendPointDTO]
    sentimentTrend: List[SentimentTrendPointDTO]
    urgencyTrend: List[UrgencyTrendPointDTO]
    warnings: List[str] = []
