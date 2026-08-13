import asyncio

import httpx

from backend.services.copilot_service.app.core.config import settings
from backend.services.copilot_service.app.core.downstream import ToolError, get_json
from backend.services.copilot_service.app.schemas.copilot import EvidenceReference
from backend.services.copilot_service.app.schemas.tools import (
    AdministrationToolInput,
    AdministrationToolResult,
    DimensionWeight,
    ImpactLevelPoints,
    ServiceHealthStatus,
    SeverityBand,
)
from backend.services.copilot_service.app.services.tool_registry import ToolDefinition, register_tool

TOOL_NAME = "administration_configuration"


async def run(client: httpx.AsyncClient, tool_input: AdministrationToolInput) -> AdministrationToolResult:
    """
    Phase 12 architecture §13.7: re-implements the same simple
    per-service `/health` loop administration_aggregator.py already
    performs (gateway_service), directly against each real domain
    service -- never via the public Gateway. Deliberately excludes
    gateway_service (calling it would violate the "no Copilot -> Gateway"
    boundary) and copilot_service itself (if this code is executing, the
    process is up -- the same rationale the Gateway's own self-health
    check already uses).
    """
    result = AdministrationToolResult()

    if tool_input.include_health:
        result.service_health = await _check_all_services(client)

    if tool_input.include_configuration:
        try:
            payload = await get_json(
                client, f"{settings.BUSINESS_IMPACT_SERVICE_URL}/api/v1/configuration/business-impact"
            )
        except ToolError as exc:
            result.error = exc.message
        else:
            if payload is not None:
                result.dimension_weights = [DimensionWeight(**item) for item in payload.get("dimension_weights", [])]
                result.impact_level_points = [
                    ImpactLevelPoints(**item) for item in payload.get("impact_level_points", [])
                ]
                result.severity_bands = [SeverityBand(**item) for item in payload.get("severity_bands", [])]
                result.evidence_references.append(
                    EvidenceReference(
                        evidence_id="configuration:business_impact",
                        source_type="configuration",
                        source_id="business_impact",
                        authority="business_impact_service",
                        timestamp=None,
                    )
                )

    return result


async def _check_all_services(client: httpx.AsyncClient) -> list[ServiceHealthStatus]:
    targets = settings.health_check_targets
    results = await asyncio.gather(*(_check_one(client, name, url) for name, url in targets.items()))
    return list(results)


async def _check_one(client: httpx.AsyncClient, service_name: str, base_url: str) -> ServiceHealthStatus:
    try:
        body = await get_json(client, f"{base_url}/health")
    except ToolError as exc:
        return ServiceHealthStatus(service=service_name, status="unavailable", detail=exc.kind)

    status = (body or {}).get("status")
    if status == "ok":
        return ServiceHealthStatus(service=service_name, status="healthy", detail="ok")
    return ServiceHealthStatus(service=service_name, status="unavailable", detail=str(status))


register_tool(
    ToolDefinition(
        name=TOOL_NAME,
        description="Report real-time platform service health and the Business Impact engine's read-only configuration (weights, point values, severity bands).",
        input_model=AdministrationToolInput,
        output_model=AdministrationToolResult,
        executor=run,
    )
)
