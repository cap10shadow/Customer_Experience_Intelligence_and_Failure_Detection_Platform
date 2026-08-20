import httpx
from fastapi import APIRouter, Depends

from backend.services.gateway_service.app.core.authorization import require_role
from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.schemas.investigation import InvestigationResponse, RootCauseActionResponse
from backend.services.gateway_service.app.services.investigation_aggregator import (
    build_investigation,
    confirm_root_cause,
    refresh_root_cause,
    reject_root_cause,
)

router = APIRouter(tags=["investigations"])


@router.get("/investigations/{incident_id}", response_model=InvestigationResponse)
async def get_investigation(
    incident_id: str,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> InvestigationResponse:
    """
    The primary vertical integration path: one Incident's full
    Investigation, aggregated from anomaly_service (incident + linked
    anomalies), root_cause_service, business_impact_service, and
    recommendation_service. `incident_id` is the central correlation key
    throughout (Batch 3 SS2) -- no separate investigation identity exists.

    A 404 here means the Incident genuinely does not exist
    (anomaly_service's own 404, propagated as-is) -- distinct from a
    downstream failure (502/503/504), and distinct from Root
    Cause/Business Impact/Recommendation legitimately not existing yet
    for a real Incident (represented as null/empty fields, not an error).
    See investigation_aggregator.build_investigation's docstring for the
    full essential/non-essential classification.
    """
    return await build_investigation(client, incident_id)


@router.patch(
    "/investigations/{incident_id}/root-cause/confirm",
    response_model=RootCauseActionResponse,
    dependencies=[Depends(require_role("operator"))],
)
async def confirm_investigation_root_cause(
    incident_id: str,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> RootCauseActionResponse:
    """
    Confirms the RootCause for an Incident (root_cause_service's own real
    capability, previously implemented but unreachable through the
    Gateway/frontend). Requires `operator` -- the same role tier
    Recommendation's decision route requires -- since this is a real
    human decision on the platform's central lifecycle object, not a read.
    """
    return await confirm_root_cause(client, incident_id)


@router.patch(
    "/investigations/{incident_id}/root-cause/reject",
    response_model=RootCauseActionResponse,
    dependencies=[Depends(require_role("operator"))],
)
async def reject_investigation_root_cause(
    incident_id: str,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> RootCauseActionResponse:
    """Rejects the RootCause for an Incident -- see `confirm_investigation_root_cause`'s docstring."""
    return await reject_root_cause(client, incident_id)


@router.post(
    "/investigations/{incident_id}/root-cause/refresh",
    response_model=RootCauseActionResponse,
    dependencies=[Depends(require_role("operator"))],
)
async def refresh_investigation_root_cause(
    incident_id: str,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> RootCauseActionResponse:
    """Re-runs Root Cause Analysis for an Incident's RootCause -- see `confirm_investigation_root_cause`'s docstring."""
    return await refresh_root_cause(client, incident_id)
