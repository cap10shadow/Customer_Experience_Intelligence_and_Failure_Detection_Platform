import httpx
from fastapi import APIRouter, Depends

from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.schemas.administration import (
    AdministrationOverviewResponse,
    IntelligenceConfigurationResponse,
)
from backend.services.gateway_service.app.services.administration_aggregator import (
    build_administration_overview,
    build_intelligence_configuration,
)

router = APIRouter(tags=["administration"])


@router.get("/administration/overview", response_model=AdministrationOverviewResponse)
async def get_administration_overview(
    client: httpx.AsyncClient = Depends(get_http_client),
) -> AdministrationOverviewResponse:
    """
    Real, just-checked service-health aggregation for Administration's
    Platform Overview (Step 7.X A-02) -- the first Gateway surface for
    the Administration workspace. Sourced entirely from every backend
    service's existing `/health` endpoint; no new backend capability.
    """
    return await build_administration_overview(client)


@router.get("/administration/intelligence-configuration", response_model=IntelligenceConfigurationResponse)
async def get_intelligence_configuration(
    client: httpx.AsyncClient = Depends(get_http_client),
) -> IntelligenceConfigurationResponse:
    """
    Read-only Business Impact configuration (Step 7.X G-05) -- real,
    currently-active engine values, sourced from business_impact_service's
    own read-only configuration endpoint. No mutation route exists here
    or anywhere in this module.
    """
    return await build_intelligence_configuration(client)
