import httpx
import pytest

from backend.services.copilot_service.app.schemas.tools import AdministrationToolInput
from backend.services.copilot_service.app.services import administration_tool as tool


def _configuration_payload():
    return {
        "dimension_weights": [{"dimension": "financial", "weight": 0.3}],
        "impact_level_points": [{"level": "high", "points": 3}],
        "severity_bands": [{"upper_bound_inclusive": 100, "level": "critical"}],
    }


def _client_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_all_seven_domain_services_are_checked_independently():
    checked_paths = []

    async def handler(request: httpx.Request) -> httpx.Response:
        checked_paths.append(str(request.url))
        if request.url.path == "/api/v1/configuration/business-impact":
            return httpx.Response(200, json=_configuration_payload())
        return httpx.Response(200, json={"status": "ok", "service": "x"})

    client = _client_for(handler)
    result = await tool.run(client, AdministrationToolInput())

    assert len(result.service_health) == 7
    assert all(s.status == "healthy" for s in result.service_health)


@pytest.mark.anyio
async def test_gateway_and_copilot_are_never_checked_directly():
    """Copilot must never call the public Gateway (§6/§20) -- confirmed here by
    asserting only the 7 real domain-service health checks occur."""
    services_checked = set()

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            services_checked.add(request.url.port)
        if request.url.path == "/api/v1/configuration/business-impact":
            return httpx.Response(200, json=_configuration_payload())
        return httpx.Response(200, json={"status": "ok", "service": "x"})

    client = _client_for(handler)
    await tool.run(client, AdministrationToolInput())

    assert 8000 not in services_checked  # gateway_service's port
    assert 8007 not in services_checked  # copilot_service's own port


@pytest.mark.anyio
async def test_one_unavailable_service_does_not_hide_the_others():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/configuration/business-impact":
            return httpx.Response(200, json=_configuration_payload())
        if request.url.port == 8003:  # anomaly_service
            raise httpx.ConnectError("connection refused", request=request)
        return httpx.Response(200, json={"status": "ok", "service": "x"})

    client = _client_for(handler)
    result = await tool.run(client, AdministrationToolInput())

    by_service = {s.service: s.status for s in result.service_health}
    assert by_service["anomaly"] == "unavailable"
    assert by_service["nlp"] == "healthy"
    assert len(result.service_health) == 7


@pytest.mark.anyio
async def test_configuration_contains_no_secret_like_field():
    client = _client_for(lambda request: httpx.Response(200, json=_configuration_payload()))
    result = await tool.run(client, AdministrationToolInput())

    dumped = result.model_dump_json().lower()
    for forbidden in ("password", "secret", "token", "api_key", "authorization", "database_url", "credential"):
        assert forbidden not in dumped


@pytest.mark.anyio
async def test_include_flags_control_which_sections_are_fetched():
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, json={"status": "ok", "service": "x"})

    client = _client_for(handler)
    result = await tool.run(client, AdministrationToolInput(include_health=False, include_configuration=False))

    assert calls == []
    assert result.service_health == []
    assert result.dimension_weights == []
