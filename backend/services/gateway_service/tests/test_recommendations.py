import uuid

import httpx
import pytest

from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.main import app

RECOMMENDATION_ID = str(uuid.uuid4())
INCIDENT_ID = "incident-42"
GENERATION_ID = str(uuid.uuid4())


def _recommendation_detail():
    return {
        "recommendation_id": RECOMMENDATION_ID,
        "incident_id": INCIDENT_ID,
        "generation_id": GENERATION_ID,
        "category": "escalate",
        "priority": "high",
        "score": 88,
        "action": "Escalate to payments team",
        "recommendation_rationale": "The timing aligns with a recent payment gateway change.",
        "priority_rationale": "High business impact warrants immediate attention.",
        "supporting_evidence": [
            {"source": "business_impact", "description": "Business impact overall severity is high", "weight": 5},
        ],
        "created_at": "2026-08-08T01:05:00Z",
    }


def _make_handler(*, status=200, body=None):
    async def handler(request: httpx.Request) -> httpx.Response:
        if status != 200:
            return httpx.Response(status)
        return httpx.Response(200, json=body if body is not None else _recommendation_detail())

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
async def test_recommendation_read_returns_real_backend_fields(override_http_client):
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/recommendations/{RECOMMENDATION_ID}")

    assert response.status_code == 200
    body = response.json()

    assert body["recommendationId"] == RECOMMENDATION_ID
    assert body["incidentId"] == INCIDENT_ID
    assert body["generationId"] == GENERATION_ID
    assert body["category"] == "escalate"
    assert body["priority"] == "high"
    assert body["score"] == 88
    assert body["action"] == "Escalate to payments team"
    assert body["recommendationRationale"] == "The timing aligns with a recent payment gateway change."
    assert body["priorityRationale"] == "High business impact warrants immediate attention."
    assert body["supportingEvidence"] == [
        {"source": "business_impact", "description": "Business impact overall severity is high", "weight": 5}
    ]
    assert body["createdAt"] == "2026-08-08T01:05:00Z"


@pytest.mark.anyio
async def test_recommendation_response_never_fabricates_lifecycle_or_future_fields(override_http_client):
    """No approve/reject/defer/decision/outcome/effectiveness/risk/alternatives fields exist on the real backend, so none may appear on the Gateway DTO."""
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/recommendations/{RECOMMENDATION_ID}")

    body = response.json()
    forbidden_keys = {
        "confidence",
        "confidenceLevel",
        "decision",
        "decisionStatus",
        "lifecycle",
        "lifecycleStage",
        "status",
        "outcome",
        "effectiveness",
        "alternatives",
        "alternativeOptions",
        "risk",
        "riskAssessment",
        "approved",
        "rejected",
        "deferred",
    }
    assert forbidden_keys.isdisjoint(body.keys())


@pytest.mark.anyio
async def test_recommendation_not_found_returns_a_real_404_not_a_generic_failure(override_http_client):
    client = _client_for(_make_handler(status=404))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/recommendations/{RECOMMENDATION_ID}")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert body["error"]["details"]["recommendationId"] == RECOMMENDATION_ID


@pytest.mark.anyio
async def test_recommendation_service_failure_fails_the_request(override_http_client):
    client = _client_for(_make_handler(status=500))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/recommendations/{RECOMMENDATION_ID}")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "DOWNSTREAM_SERVICE_FAILURE"


@pytest.mark.anyio
async def test_recommendation_service_unavailable_maps_to_503(override_http_client):
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/recommendations/{RECOMMENDATION_ID}")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DOWNSTREAM_SERVICE_UNAVAILABLE"


@pytest.mark.anyio
async def test_recommendation_id_traceability_is_preserved(override_http_client):
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/recommendations/{RECOMMENDATION_ID}")

    body = response.json()
    assert body["recommendationId"] == RECOMMENDATION_ID
    assert body["incidentId"] == INCIDENT_ID


@pytest.mark.anyio
async def test_no_direct_frontend_write_route_exists(override_http_client):
    """Part 4 is read-only: the Gateway must not expose any write/decision endpoint for Recommendations."""
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        for method in ("post", "put", "patch", "delete"):
            response = await test_client.request(method, f"/api/v1/recommendations/{RECOMMENDATION_ID}")
            assert response.status_code == 405
