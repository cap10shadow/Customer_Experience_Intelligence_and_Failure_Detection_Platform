from typing import Any, Dict

import httpx

from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.core.downstream import get_json
from backend.services.gateway_service.app.core.errors import DownstreamServiceError
from backend.services.gateway_service.app.schemas.analytics import (
    AnalyticsResponse,
    CategoryTrendPointDTO,
    RegionTrendPointDTO,
    SentimentTrendPointDTO,
    UrgencyTrendPointDTO,
    VolumeTrendPointDTO,
)


async def build_analytics(client: httpx.AsyncClient, days: int) -> AnalyticsResponse:
    """
    Retrieves anomaly_service's real trend summary (`GET /api/v1/trends`,
    which already aggregates complaint volume, categories, regions,
    sentiment, and urgency in one call -- Part 5's backend capability
    audit found this single existing endpoint, so the Gateway issues one
    downstream call rather than five (Batch 3 SS22's "no unnecessary
    calls" principle).

    This is treated as essential, unlike Dashboard's non-essential trend
    enrichment: Analytics' Trend Analysis section has nothing else to
    build from, so a genuine downstream failure here fails the whole
    request rather than degrading into a request that returns success
    with no real content (Batch 4C SS15's per-endpoint partial-failure
    judgment: essential when the missing dependency is everything the
    endpoint exists to provide).
    """
    trends = await get_json(client, f"{settings.ANOMALY_SERVICE_URL}/api/v1/trends", params={"days": days})
    if trends is None:
        raise DownstreamServiceError("Trend data could not be retrieved.")
    return _to_response(trends)


def _to_response(trends: Dict[str, Any]) -> AnalyticsResponse:
    return AnalyticsResponse(
        period=trends["period"],
        volumeTrend=[
            VolumeTrendPointDTO(date=str(point["date"]), count=point["count"]) for point in trends.get("complaint_volume", [])
        ],
        categoryTrend=[
            CategoryTrendPointDTO(category=point["category"], count=point["count"]) for point in trends.get("categories", [])
        ],
        regionTrend=[RegionTrendPointDTO(region=point["region"], count=point["count"]) for point in trends.get("regions", [])],
        sentimentTrend=[
            SentimentTrendPointDTO(
                date=str(point["date"]), averageScore=point["average_score"], labelCounts=point.get("label_counts", {})
            )
            for point in trends.get("sentiment", [])
        ],
        urgencyTrend=[
            UrgencyTrendPointDTO(urgency=point["urgency"], count=point["count"]) for point in trends.get("urgency", [])
        ],
        warnings=[],
    )
