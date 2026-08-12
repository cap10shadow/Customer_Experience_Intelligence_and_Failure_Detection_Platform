import httpx
import pytest

from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.main import app


def _json(payload, status_code=200):
    return httpx.Response(status_code, json=payload)


def _service_id_for_url(url: str):
    for service_id, base_url in settings.downstream_service_urls.items():
        if base_url in url:
            return service_id
    return None


def _make_handler(*, unavailable=(), failing=()):
    """
    Builds an async httpx.MockTransport handler standing in for every
    backend service's own `/health` endpoint, routed by host.

    unavailable: service ids whose connection fails outright (unreachable).
    failing: service ids whose `/health` responds with a non-2xx status.
    """

    async def handler(request: httpx.Request) -> httpx.Response:
        service_id = _service_id_for_url(str(request.url))
        if service_id is None:
            raise AssertionError(f"Unexpected downstream call: {request.url}")
        if service_id in unavailable:
            raise httpx.ConnectError("connection refused", request=request)
        if service_id in failing:
            return httpx.Response(503)
        return _json({"status": "ok", "service": f"{service_id}_service"})

    return handler


def _client_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def override_http_client():
    def _apply(client: httpx.AsyncClient):
        app.dependency_overrides[get_http_client] = lambda: client

    yield _apply
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_administration_overview_reports_every_service_as_healthy(override_http_client):
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/administration/overview")

    assert response.status_code == 200
    body = response.json()
    assert len(body["services"]) == 9  # 8 downstream services + the Gateway itself
    assert all(service["status"] == "healthy" for service in body["services"])
    assert body["warnings"] == []
    ids = {service["id"] for service in body["services"]}
    assert ids == {
        "gateway",
        "ingestion",
        "nlp",
        "anomaly",
        "root_cause",
        "business_impact",
        "recommendation",
        "copilot",
        "evaluation",
    }


@pytest.mark.anyio
async def test_administration_overview_reports_an_unreachable_service_honestly(override_http_client):
    client = _client_for(_make_handler(unavailable=("copilot",)))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/administration/overview")

    assert response.status_code == 200
    body = response.json()
    copilot = next(service for service in body["services"] if service["id"] == "copilot")
    assert copilot["status"] == "unavailable"
    other_statuses = {service["status"] for service in body["services"] if service["id"] != "copilot"}
    assert other_statuses == {"healthy"}
    assert any("Copilot Service is unavailable" in warning for warning in body["warnings"])


@pytest.mark.anyio
async def test_administration_overview_reports_a_non_2xx_health_response_as_unavailable(override_http_client):
    client = _client_for(_make_handler(failing=("nlp",)))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/administration/overview")

    assert response.status_code == 200
    body = response.json()
    nlp = next(service for service in body["services"] if service["id"] == "nlp")
    assert nlp["status"] == "unavailable"


@pytest.mark.anyio
async def test_administration_overview_survives_every_downstream_service_being_unavailable(override_http_client):
    all_ids = tuple(settings.downstream_service_urls.keys())
    client = _client_for(_make_handler(unavailable=all_ids))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/administration/overview")

    assert response.status_code == 200
    body = response.json()
    gateway_entry = next(service for service in body["services"] if service["id"] == "gateway")
    assert gateway_entry["status"] == "healthy"  # the Gateway itself is up if it answered the request at all
    downstream_statuses = {service["status"] for service in body["services"] if service["id"] != "gateway"}
    assert downstream_statuses == {"unavailable"}
    assert len(body["warnings"]) == len(all_ids)


@pytest.mark.anyio
async def test_administration_overview_never_invents_a_status_beyond_healthy_or_unavailable(override_http_client):
    client = _client_for(_make_handler(unavailable=("recommendation",)))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/administration/overview")

    body = response.json()
    statuses = {service["status"] for service in body["services"]}
    assert statuses <= {"healthy", "unavailable"}


@pytest.mark.anyio
async def test_administration_overview_calls_health_at_service_root_not_under_api_v1(override_http_client):
    """Each backend service's own /health lives at its root, not under /api/v1 -- the Gateway must call it as-is."""
    seen_paths = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        return _json({"status": "ok", "service": "x"})

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/administration/overview")

    assert response.status_code == 200
    assert seen_paths  # at least the 8 downstream calls happened
    assert all(path == "/health" for path in seen_paths)


def _configuration_payload():
    return {
        "dimension_weights": [
            {"dimension": "financial", "weight": 0.35},
            {"dimension": "customer", "weight": 0.25},
            {"dimension": "operational", "weight": 0.15},
            {"dimension": "sla", "weight": 0.15},
            {"dimension": "reputation", "weight": 0.10},
        ],
        "impact_level_points": [
            {"level": "none", "points": 0},
            {"level": "low", "points": 25},
            {"level": "medium", "points": 50},
            {"level": "high", "points": 75},
            {"level": "critical", "points": 100},
        ],
        "severity_bands": [
            {"upper_bound_inclusive": 20, "level": "none"},
            {"upper_bound_inclusive": 40, "level": "low"},
            {"upper_bound_inclusive": 60, "level": "medium"},
            {"upper_bound_inclusive": 80, "level": "high"},
        ],
    }


@pytest.mark.anyio
async def test_intelligence_configuration_returns_real_values_from_business_impact_service(override_http_client):
    async def handler(request: httpx.Request) -> httpx.Response:
        assert "/api/v1/configuration/business-impact" in str(request.url)
        return _json(_configuration_payload())

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/administration/intelligence-configuration")

    assert response.status_code == 200
    body = response.json()
    weight_items = [item for item in body["items"] if item["id"].startswith("business-impact-weight-")]
    assert len(weight_items) == 5
    financial = next(item for item in weight_items if item["id"] == "business-impact-weight-financial")
    assert financial["currentValue"] == "35%"

    severity_item = next(item for item in body["items"] if item["id"] == "business-impact-severity-bands")
    assert "None ≤20" in severity_item["currentValue"]
    assert "High ≤80" in severity_item["currentValue"]

    points_item = next(item for item in body["items"] if item["id"] == "business-impact-level-points")
    assert "Critical=100" in points_item["currentValue"]


@pytest.mark.anyio
async def test_intelligence_configuration_items_have_no_edit_affordance_fields(override_http_client):
    """Every item carries only display fields -- no editable/version/mutation-related field is ever included."""
    client = _client_for(lambda request: _json(_configuration_payload()))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/administration/intelligence-configuration")

    body = response.json()
    for item in body["items"]:
        assert set(item.keys()) == {"id", "name", "whatItIs", "governs", "currentValue"}


@pytest.mark.anyio
async def test_intelligence_configuration_exposes_no_secrets(override_http_client):
    client = _client_for(lambda request: _json(_configuration_payload()))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/administration/intelligence-configuration")

    body_text = response.text.lower()
    for forbidden_term in ("password", "secret", "token", "api_key", "database_url", "credential"):
        assert forbidden_term not in body_text


@pytest.mark.anyio
async def test_intelligence_configuration_downstream_unavailable_maps_to_503(override_http_client):
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/administration/intelligence-configuration")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DOWNSTREAM_SERVICE_UNAVAILABLE"


@pytest.mark.anyio
async def test_intelligence_configuration_downstream_failure_maps_to_502(override_http_client):
    client = _client_for(lambda request: httpx.Response(500))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/administration/intelligence-configuration")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "DOWNSTREAM_SERVICE_FAILURE"


@pytest.mark.anyio
async def test_intelligence_configuration_has_no_mutation_route(override_http_client):
    client = _client_for(lambda request: _json(_configuration_payload()))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        for method in ("post", "put", "patch", "delete"):
            response = await test_client.request(method, "/api/v1/administration/intelligence-configuration")
            assert response.status_code == 405
