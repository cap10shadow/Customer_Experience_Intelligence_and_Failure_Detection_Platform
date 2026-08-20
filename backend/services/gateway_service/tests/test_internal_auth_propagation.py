"""
Tests for the Gateway's outbound internal-service credential and
principal-propagation headers (Phase 13 Batch 4, AD-5) -- the
recommendation-decision PATCH and Copilot POST calls, the two routes
§14 of the frozen architecture names. Uses the same
`httpx.MockTransport`-backed `get_http_client` override every other
gateway_service test in this suite already uses, capturing the outbound
request's headers rather than asserting on response content.
"""

import uuid

import httpx
import pytest

from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.main import app
from backend.shared.config.settings import settings as shared_settings
from backend.shared.security.internal_auth import INTERNAL_SECRET_HEADER, PRINCIPAL_USER_ID_HEADER
from backend.services.gateway_service.tests.conftest import TEST_PRINCIPAL


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def override_http_client():
    def _apply(client: httpx.AsyncClient):
        app.dependency_overrides[get_http_client] = lambda: client

    yield _apply
    app.dependency_overrides.pop(get_http_client, None)


def _capturing_client(captured_headers: list, *, status: int = 200, body: dict | None = None) -> httpx.AsyncClient:
    async def handler(request: httpx.Request) -> httpx.Response:
        captured_headers.append(request.headers)
        return httpx.Response(status, json=body or {})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def _call(path: str, *, method: str = "GET", json: dict | None = None) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        if method == "PATCH":
            return await client.patch(path, json=json)
        if method == "GET":
            return await client.get(path)
        return await client.post(path, json=json)


@pytest.mark.anyio
async def test_recommendation_decision_patch_attaches_the_internal_secret(override_http_client):
    captured: list = []
    override_http_client(
        _capturing_client(
            captured,
            body={
                "recommendation_id": str(uuid.uuid4()),
                "incident_id": "INC-1",
                "dataset_id": str(uuid.uuid4()),
                "dataset_version_id": str(uuid.uuid4()),
                "generation_id": str(uuid.uuid4()),
                "category": "escalate",
                "priority": "high",
                "score": 1,
                "action": "x",
                "recommendation_rationale": "x",
                "priority_rationale": "x",
                "supporting_evidence": [],
                "created_at": "2026-08-08T01:05:00Z",
            },
        )
    )

    await _call(f"/api/v1/recommendations/{uuid.uuid4()}/decision", method="PATCH", json={"decision": "approved"})

    assert len(captured) == 1
    assert captured[0][INTERNAL_SECRET_HEADER] == shared_settings.INTERNAL_SERVICE_SECRET


@pytest.mark.anyio
async def test_recommendation_decision_patch_attaches_the_gateway_attested_principal_user_id(override_http_client):
    captured: list = []
    override_http_client(
        _capturing_client(
            captured,
            body={
                "recommendation_id": str(uuid.uuid4()),
                "incident_id": "INC-1",
                "dataset_id": str(uuid.uuid4()),
                "dataset_version_id": str(uuid.uuid4()),
                "generation_id": str(uuid.uuid4()),
                "category": "escalate",
                "priority": "high",
                "score": 1,
                "action": "x",
                "recommendation_rationale": "x",
                "priority_rationale": "x",
                "supporting_evidence": [],
                "created_at": "2026-08-08T01:05:00Z",
            },
        )
    )

    await _call(f"/api/v1/recommendations/{uuid.uuid4()}/decision", method="PATCH", json={"decision": "approved"})

    assert captured[0][PRINCIPAL_USER_ID_HEADER] == str(TEST_PRINCIPAL.user_id)


@pytest.mark.anyio
async def test_copilot_message_attaches_the_internal_secret_and_principal(override_http_client):
    captured: list = []
    override_http_client(
        _capturing_client(
            captured,
            body={
                "answer": "x",
                "key_findings": [],
                "evidence_references": [],
                "related_entities": [],
                "visualization_hint": None,
                "limitations": [],
                "conversation_id": str(uuid.uuid4()),
                "request_id": str(uuid.uuid4()),
            },
        )
    )

    await _call("/api/v1/copilot/messages", method="POST", json={"message": "hello"})

    assert len(captured) == 1
    assert captured[0][INTERNAL_SECRET_HEADER] == shared_settings.INTERNAL_SERVICE_SECRET
    assert captured[0][PRINCIPAL_USER_ID_HEADER] == str(TEST_PRINCIPAL.user_id)


@pytest.mark.anyio
async def test_a_read_only_downstream_call_does_not_carry_the_internal_secret(override_http_client):
    """§14: read-only aggregation calls (e.g. GET recommendation) are deliberately unchanged -- not every downstream call should carry the credential."""
    captured: list = []
    override_http_client(
        _capturing_client(
            captured,
            body={
                "recommendation_id": str(uuid.uuid4()),
                "incident_id": "INC-1",
                "dataset_id": str(uuid.uuid4()),
                "dataset_version_id": str(uuid.uuid4()),
                "generation_id": str(uuid.uuid4()),
                "category": "escalate",
                "priority": "high",
                "score": 1,
                "action": "x",
                "recommendation_rationale": "x",
                "priority_rationale": "x",
                "supporting_evidence": [],
                "created_at": "2026-08-08T01:05:00Z",
            },
        )
    )

    await _call(f"/api/v1/recommendations/{uuid.uuid4()}", method="GET")

    assert INTERNAL_SECRET_HEADER not in captured[0]


def test_gateway_exposes_no_internal_route():
    """§13: `/internal/events/*` must never be reachable through the public Gateway."""
    internal_paths = [route.path for route in app.routes if getattr(route, "path", "").startswith("/internal")]

    assert internal_paths == []
