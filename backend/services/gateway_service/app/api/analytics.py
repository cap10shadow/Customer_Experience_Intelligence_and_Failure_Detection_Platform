import httpx
from fastapi import APIRouter, Depends, Query

from backend.services.gateway_service.app.core.errors import GatewayValidationError
from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.schemas.analytics import AnalyticsResponse
from backend.services.gateway_service.app.services.analytics_aggregator import build_analytics

router = APIRouter(tags=["analytics"])

# Mirrors frontend/src/workspaces/analytics/types.ts's AnalysisPeriod exactly.
# 'last-quarter' -> 90 is an approximation (anomaly_service has no calendar-
# quarter concept, only a trailing day count); 'last-12-months' -> 365 sits
# exactly at the backend's `days` ceiling (`ge=1, le=365`).
_PERIOD_TO_DAYS = {"last-30-days": 30, "last-quarter": 90, "last-12-months": 365}


@router.get("/analytics/trends", response_model=AnalyticsResponse)
async def get_analytics_trends(
    period: str = Query(default="last-30-days"),
    client: httpx.AsyncClient = Depends(get_http_client),
) -> AnalyticsResponse:
    """
    Real trend data only (Part 5's scope). Named `/analytics/trends`, not
    the bare `/analytics` the earlier architecture sketch used, because
    that is the only genuine Analytics capability the backend has today
    (Batch 1 SS24's "no fake API surface" rule) -- Pattern Discovery,
    Organizational Insights, Strategic Opportunities, and Recommendation
    Effectiveness have no backend capability whatsoever (Part 5's audit)
    and so have no corresponding route here.

    NO-FAKE-FILTER RULE (same as Dashboard's `/dashboard`): `period` must
    be one of AnalyticsContext's own three values; anything else is
    rejected with 400 rather than silently substituted.
    """
    if period not in _PERIOD_TO_DAYS:
        raise GatewayValidationError(
            f"period must be one of {list(_PERIOD_TO_DAYS)}.",
            details={"period": period},
        )

    return await build_analytics(client, _PERIOD_TO_DAYS[period])
