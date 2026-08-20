import uuid

import httpx
import pytest

from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.main import app

RECOMMENDATION_ID = str(uuid.uuid4())
INCIDENT_ID = "incident-42"
DATASET_ID = str(uuid.uuid4())
DATASET_VERSION_ID = str(uuid.uuid4())
GENERATION_ID = str(uuid.uuid4())


def _recommendation_detail():
    return {
        "recommendation_id": RECOMMENDATION_ID,
        "incident_id": INCIDENT_ID,
        "dataset_id": DATASET_ID,
        "dataset_version_id": DATASET_VERSION_ID,
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
    """
    No confidence/lifecycle/outcome/effectiveness/risk/alternatives field
    exists on the real backend, so none may appear on the Gateway DTO.
    `decision`/`decisionNote`/`decidedAt` (Step 7.X G-01) are the one
    exception -- they are real fields now, correctly present (as `null`
    for a never-decided Recommendation, exercised separately below).
    """
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/recommendations/{RECOMMENDATION_ID}")

    body = response.json()
    forbidden_keys = {
        "confidence",
        "confidenceLevel",
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
        "actorId",
        "userId",
        "owner",
        "approvalAuthority",
        "decidedBy",
    }
    assert forbidden_keys.isdisjoint(body.keys())


@pytest.mark.anyio
async def test_recommendation_read_exposes_null_decision_fields_when_never_decided(override_http_client):
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/recommendations/{RECOMMENDATION_ID}")

    body = response.json()
    assert body["decision"] is None
    assert body["decisionNote"] is None
    assert body["decidedAt"] is None


@pytest.mark.anyio
async def test_recommendation_read_exposes_real_decision_fields_once_persisted(override_http_client):
    detail = _recommendation_detail()
    detail["decision"] = "approved"
    detail["decision_note"] = "Looks correct."
    detail["decided_at"] = "2026-08-12T10:00:00Z"
    client = _client_for(_make_handler(body=detail))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/recommendations/{RECOMMENDATION_ID}")

    body = response.json()
    assert body["decision"] == "approved"
    assert body["decisionNote"] == "Looks correct."
    assert body["decidedAt"] == "2026-08-12T10:00:00Z"


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
    """
    The Recommendation resource itself remains read-only -- no
    POST/PUT/PATCH/DELETE against `/recommendations/{id}` directly. The
    one deliberate exception is the decision sub-resource (Step 7.X
    G-01, tested separately below): `/recommendations/{id}/decision`.
    """
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        for method in ("post", "put", "patch", "delete"):
            response = await test_client.request(method, f"/api/v1/recommendations/{RECOMMENDATION_ID}")
            assert response.status_code == 405


@pytest.mark.anyio
async def test_patch_decision_forwards_request_and_maps_response(override_http_client):
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["body"] = request.content
        detail = _recommendation_detail()
        detail["decision"] = "approved"
        detail["decision_note"] = "Reviewed and approved."
        detail["decided_at"] = "2026-08-12T10:00:00Z"
        return httpx.Response(200, json=detail)

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.patch(
            f"/api/v1/recommendations/{RECOMMENDATION_ID}/decision",
            json={"decision": "approved", "note": "Reviewed and approved."},
        )

    assert response.status_code == 200
    assert captured["method"] == "PATCH"
    assert captured["url"].endswith(f"/api/v1/recommendations/{RECOMMENDATION_ID}/decision")
    body = response.json()
    assert body["decision"] == "approved"
    assert body["decisionNote"] == "Reviewed and approved."
    assert body["decidedAt"] == "2026-08-12T10:00:00Z"


@pytest.mark.anyio
async def test_patch_decision_rejects_invalid_decision_value(override_http_client):
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.patch(
            f"/api/v1/recommendations/{RECOMMENDATION_ID}/decision", json={"decision": "maybe"}
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_patch_decision_rejects_actor_field(override_http_client):
    """Even if a caller supplies actor_id/decidedAt, the Gateway's request schema drops it -- no such field is ever forwarded."""
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content
        return httpx.Response(200, json=_recommendation_detail())

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.patch(
            f"/api/v1/recommendations/{RECOMMENDATION_ID}/decision",
            json={"decision": "approved", "actor_id": "user-1", "decidedAt": "2020-01-01T00:00:00Z"},
        )

    assert response.status_code == 200
    assert b"actor_id" not in captured["body"]
    assert b"decidedAt" not in captured["body"]


@pytest.mark.anyio
async def test_patch_decision_not_found_returns_a_real_404(override_http_client):
    client = _client_for(_make_handler(status=404))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.patch(
            f"/api/v1/recommendations/{RECOMMENDATION_ID}/decision", json={"decision": "approved"}
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.anyio
async def test_patch_decision_downstream_failure_maps_to_502(override_http_client):
    client = _client_for(_make_handler(status=500))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.patch(
            f"/api/v1/recommendations/{RECOMMENDATION_ID}/decision", json={"decision": "approved"}
        )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "DOWNSTREAM_SERVICE_FAILURE"
