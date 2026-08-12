import httpx
from fastapi import APIRouter, Depends

from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.schemas.investigation import InvestigationResponse
from backend.services.gateway_service.app.services.investigation_aggregator import build_investigation

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
