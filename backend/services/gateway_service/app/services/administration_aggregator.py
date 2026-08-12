import asyncio

import httpx

from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.core.downstream import get_json
from backend.services.gateway_service.app.core.errors import GatewayError
from backend.services.gateway_service.app.schemas.administration import (
    AdministrationOverviewResponse,
    ServiceHealthDTO,
)

# (id, display name) pairs, in a fixed, deterministic order -- matches
# GatewaySettings.downstream_service_urls's keys exactly (core/config.py),
# plus the Gateway itself, which does not need an HTTP round-trip: if this
# code is executing, the Gateway process is, by definition, up.
_DOWNSTREAM_SERVICES: list[tuple[str, str]] = [
    ("ingestion", "Ingestion Service"),
    ("nlp", "NLP Service"),
    ("anomaly", "Anomaly Service"),
    ("root_cause", "Root Cause Service"),
    ("business_impact", "Business Impact Service"),
    ("recommendation", "Recommendation Service"),
    ("copilot", "Copilot Service"),
    ("evaluation", "Evaluation Service"),
]


async def build_administration_overview(client: httpx.AsyncClient) -> AdministrationOverviewResponse:
    """
    Aggregates real, just-checked reachability for every backend service
    from each service's own existing `/health` endpoint (no new backend
    capability). Every service is checked independently and concurrently;
    one service being unavailable never fails the whole response or hides
    the other services' real status -- each is represented explicitly as
    "healthy" or "unavailable", never silently omitted or fabricated.
    """
    warnings: list[str] = []

    tasks = [
        asyncio.create_task(_check_service_health(client, service_id, display_name))
        for service_id, display_name in _DOWNSTREAM_SERVICES
    ]
    checked = await asyncio.gather(*tasks)

    services = [_gateway_self_health(), *checked]
    for service in services:
        if service.status == "unavailable":
            warnings.append(f"{service.name} is unavailable ({service.detail}).")

    return AdministrationOverviewResponse(services=services, warnings=warnings)


def _gateway_self_health() -> ServiceHealthDTO:
    return ServiceHealthDTO(id="gateway", name="Gateway Service", status="healthy", detail="ok")


async def _check_service_health(client: httpx.AsyncClient, service_id: str, display_name: str) -> ServiceHealthDTO:
    url = f"{settings.downstream_service_urls[service_id]}/health"
    try:
        body = await get_json(client, url)
    except GatewayError as exc:
        return ServiceHealthDTO(id=service_id, name=display_name, status="unavailable", detail=exc.code)

    # A service's /health endpoint always returns 200 with a JSON body
    # (`{"status": "ok", "service": "<name>"}`) when reachable -- get_json
    # only returns None for a 404, which no /health route ever produces.
    status = (body or {}).get("status")
    if status == "ok":
        return ServiceHealthDTO(id=service_id, name=display_name, status="healthy", detail="ok")
    return ServiceHealthDTO(id=service_id, name=display_name, status="unavailable", detail=str(status))
