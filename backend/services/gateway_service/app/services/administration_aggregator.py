import asyncio

import httpx

from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.core.downstream import get_json
from backend.services.gateway_service.app.core.errors import DownstreamServiceError, GatewayError
from backend.services.gateway_service.app.schemas.administration import (
    AdministrationOverviewResponse,
    ConfigurationItemDTO,
    IntelligenceConfigurationResponse,
    ServiceHealthDTO,
)

# Static, human-readable narration for each real Business Impact
# configuration value (Step 7.X G-05) -- business_impact_service's
# configuration endpoint returns only raw values, not their business
# meaning, matching Administration's own established descriptive style
# (see the frontend's prior hardcoded CONFIGURATION_ITEMS). Keyed by
# ImpactDimension value; the Gateway does not import
# business_impact_service's domain enum (DATA-002), so this is a plain
# dict keyed by the same string values the response already carries.
_DIMENSION_NAME = {
    "financial": "Financial Impact Weight",
    "customer": "Customer Impact Weight",
    "operational": "Operational Impact Weight",
    "sla": "SLA Impact Weight",
    "reputation": "Reputation Impact Weight",
}
_DIMENSION_WHAT_IT_IS = "The relative weight this dimension carries in the overall weighted business impact score."
_DIMENSION_GOVERNS = (
    "Determines how much this dimension contributes to an Incident's overall business score and severity "
    "classification, relative to the other four dimensions."
)

_LEVEL_ORDER = ["none", "low", "medium", "high", "critical"]

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


async def build_intelligence_configuration(client: httpx.AsyncClient) -> IntelligenceConfigurationResponse:
    """
    Read-only Intelligence Configuration (Step 7.X G-05): fetches
    business_impact_service's real, currently-active engine configuration
    and maps it into the frontend's existing `ConfigurationItem` shape.
    The Gateway supplies only static, human-readable narration
    (`name`/`whatItIs`/`governs`) -- `currentValue` always comes from the
    real fetched response, never a hardcoded copy. No aggregation across
    multiple services is needed (unlike Platform Overview): this is a
    single essential downstream call, matching Recommendation's own
    single-service read pattern.
    """
    configuration = await get_json(
        client, f"{settings.BUSINESS_IMPACT_SERVICE_URL}/api/v1/configuration/business-impact"
    )
    if configuration is None:
        raise DownstreamServiceError("business_impact_service's configuration endpoint returned no data.")
    items = [
        *_dimension_weight_items(configuration.get("dimension_weights", [])),
        _severity_bands_item(configuration.get("severity_bands", [])),
        _impact_level_points_item(configuration.get("impact_level_points", [])),
    ]
    return IntelligenceConfigurationResponse(items=items)


def _dimension_weight_items(dimension_weights: list) -> list[ConfigurationItemDTO]:
    return [
        ConfigurationItemDTO(
            id=f"business-impact-weight-{entry['dimension']}",
            name=_DIMENSION_NAME.get(entry["dimension"], entry["dimension"].title()),
            whatItIs=_DIMENSION_WHAT_IT_IS,
            governs=_DIMENSION_GOVERNS,
            currentValue=f"{entry['weight'] * 100:.0f}%",
        )
        for entry in dimension_weights
    ]


def _severity_bands_item(severity_bands: list) -> ConfigurationItemDTO:
    ordered = sorted(severity_bands, key=lambda entry: entry["upper_bound_inclusive"])
    formatted = ", ".join(f"{entry['level'].title()} ≤{entry['upper_bound_inclusive']}" for entry in ordered)
    return ConfigurationItemDTO(
        id="business-impact-severity-bands",
        name="Business Impact Severity Bands",
        whatItIs="The weighted-business-score thresholds that classify an Incident's overall severity.",
        governs="Determines which ImpactLevel (None/Low/Medium/High/Critical) an Incident's overall weighted business score is classified into.",
        currentValue=formatted or "No bands configured",
    )


def _impact_level_points_item(impact_level_points: list) -> ConfigurationItemDTO:
    ordered = sorted(impact_level_points, key=lambda entry: _LEVEL_ORDER.index(entry["level"]) if entry["level"] in _LEVEL_ORDER else len(_LEVEL_ORDER))
    formatted = ", ".join(f"{entry['level'].title()}={entry['points']}" for entry in ordered)
    return ConfigurationItemDTO(
        id="business-impact-level-points",
        name="Impact Level Point Values",
        whatItIs="The point value assigned to each ImpactLevel when computing a dimension's contribution to the overall weighted business score.",
        governs="Determines how much each dimension's classified ImpactLevel contributes numerically to the overall business score.",
        currentValue=formatted or "No point values configured",
    )
