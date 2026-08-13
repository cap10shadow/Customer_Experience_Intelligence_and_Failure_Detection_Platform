import json

import httpx
import pytest

from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.main import app

CONVERSATION_ID = "11111111-1111-1111-1111-111111111111"


def _copilot_message_response(**overrides):
    body = {
        "answer": "Copilot tool orchestration is not yet implemented.",
        "key_findings": [],
        "evidence_references": [],
        "related_entities": [],
        "visualization_hint": None,
        "limitations": ["Tool orchestration and evidence retrieval are not yet implemented (Phase 12 Batch 1)."],
        "conversation_id": CONVERSATION_ID,
        "request_id": "downstream-request-id",
    }
    body.update(overrides)
    return body


def _make_handler(*, status=200, body=None, captured_requests=None):
    async def handler(request: httpx.Request) -> httpx.Response:
        if captured_requests is not None:
            # `.content` must be read here, while the transport still has
            # the body available -- matches the established pattern in
            # test_recommendations.py's test_patch_decision_forwards_request_and_maps_response.
            captured_requests.append(request)
        if status != 200:
            return httpx.Response(status)
        return httpx.Response(200, json=body if body is not None else _copilot_message_response())

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
async def test_successful_forward_maps_response_to_camel_case(override_http_client):
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.post("/api/v1/copilot/messages", json={"message": "What is happening?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Copilot tool orchestration is not yet implemented."
    assert body["keyFindings"] == []
    assert body["evidenceReferences"] == []
    assert body["relatedEntities"] == []
    assert body["visualizationHint"] is None
    assert body["limitations"] == [
        "Tool orchestration and evidence retrieval are not yet implemented (Phase 12 Batch 1)."
    ]
    assert body["conversationId"] == CONVERSATION_ID
    assert body["requestId"] == "downstream-request-id"


@pytest.mark.anyio
async def test_request_body_is_forwarded_with_snake_case_and_workspace_context(override_http_client):
    captured: list = []
    client = _client_for(_make_handler(captured_requests=captured))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        await test_client.post(
            "/api/v1/copilot/messages",
            json={
                "message": "Why is West region trending up?",
                "conversationId": CONVERSATION_ID,
                "workspaceContext": {"workspace": "analytics", "timeRange": "last_7_days"},
            },
        )

    assert len(captured) == 1
    forwarded_body = json.loads(captured[0].content)
    assert forwarded_body["message"] == "Why is West region trending up?"
    assert forwarded_body["conversation_id"] == CONVERSATION_ID
    assert forwarded_body["workspace_context"]["workspace"] == "analytics"
    assert forwarded_body["workspace_context"]["time_range"] == "last_7_days"


@pytest.mark.anyio
async def test_missing_message_returns_422_without_calling_copilot(override_http_client):
    captured: list = []
    client = _client_for(_make_handler(captured_requests=captured))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.post("/api/v1/copilot/messages", json={})

    assert response.status_code == 422
    assert captured == []


@pytest.mark.anyio
async def test_copilot_service_failure_maps_to_502(override_http_client):
    client = _client_for(_make_handler(status=500))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.post("/api/v1/copilot/messages", json={"message": "hello"})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "DOWNSTREAM_SERVICE_FAILURE"


@pytest.mark.anyio
async def test_copilot_service_unavailable_maps_to_503(override_http_client):
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.post("/api/v1/copilot/messages", json={"message": "hello"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DOWNSTREAM_SERVICE_UNAVAILABLE"


@pytest.mark.anyio
async def test_copilot_service_timeout_maps_to_504(override_http_client):
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.post("/api/v1/copilot/messages", json={"message": "hello"})

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "DOWNSTREAM_TIMEOUT"


@pytest.mark.anyio
async def test_x_request_id_is_forwarded_to_copilot_service(override_http_client):
    captured: list = []
    client = _client_for(_make_handler(captured_requests=captured))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.post(
            "/api/v1/copilot/messages",
            json={"message": "hello"},
            headers={"X-Request-ID": "test-request-id"},
        )

    assert response.headers["X-Request-ID"] == "test-request-id"
    assert len(captured) == 1
    assert captured[0].headers["X-Request-ID"] == "test-request-id"
