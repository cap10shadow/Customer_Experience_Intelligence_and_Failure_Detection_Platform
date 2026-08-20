from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Query

from backend.services.gateway_service.app.core.errors import GatewayValidationError
from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.schemas.dashboard import DashboardResponse
from backend.services.gateway_service.app.services.dashboard_aggregator import DashboardQuery, build_dashboard

router = APIRouter(tags=["dashboard"])

_ALLOWED_TIME_RANGES = ("current", "24h", "7d", "30d")


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    datasetId: str = Query(..., description="The Dataset this dashboard is scoped to."),
    timeRange: str = Query(default="current"),
    region: Optional[str] = Query(default=None),
    businessUnit: Optional[str] = Query(default=None),
    productScope: Optional[str] = Query(default=None),
    userScope: Optional[str] = Query(default=None),
    client: httpx.AsyncClient = Depends(get_http_client),
) -> DashboardResponse:
    """
    Aggregated Dashboard read model, assembled from anomaly_service
    (incidents, trends), recommendation_service, root_cause_service, and
    business_impact_service -- Supporting Evidence is deliberately absent
    (Batch 2 SS2: no backend capability exists for it in Step 7).

    query params mirror DashboardContext's existing scope fields
    (timeRange/region/businessUnit/productScope/userScope) so the Gateway
    is ready for the day a filter bar actually calls setRegion/etc.

    NO-FAKE-FILTER RULE: only `timeRange` is genuinely applied today (it
    maps to the real `days` window `/trends/daily` accepts).
    region/businessUnit/productScope/userScope are rejected with 400 if
    given a real value -- there is no downstream capability that can
    actually filter by any of them, and silently accepting them would
    misrepresent the response as filtered when it isn't.
    """
    if timeRange not in _ALLOWED_TIME_RANGES:
        raise GatewayValidationError(
            f"timeRange must be one of {list(_ALLOWED_TIME_RANGES)}.",
            details={"timeRange": timeRange},
        )

    unsupported_filters = {
        field: value
        for field, value in (
            ("region", region),
            ("businessUnit", businessUnit),
            ("productScope", productScope),
            ("userScope", userScope),
        )
        if value
    }
    if unsupported_filters:
        raise GatewayValidationError(
            "These Dashboard filters are not yet supported by any backend capability: "
            f"{', '.join(sorted(unsupported_filters))}.",
            details={"unsupportedFilters": sorted(unsupported_filters), "scope": "Step 7.X"},
        )

    query = DashboardQuery(time_range=timeRange, dataset_id=datasetId)
    return await build_dashboard(client, query)
