"""
Tests for `POST /api/v1/copilot/messages`'s HTTP-level contract
(request validation, conversation-id/request-id behavior, response
shape). As of Phase 12 Batch 3, the route runs the real bounded
orchestration graph; with no LLM provider configured in this test
environment (the default `NullLLMProvider`), it deterministically
produces one honest "no language model configured" answer with no tool
calls -- see `tests/test_orchestrator_graph.py` for tool-selection/
evidence/iteration-bound coverage using a scripted `FakeLLMProvider`.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.services.copilot_service.app.main import app

import httpx

from backend.services.copilot_service.app.dependencies.http_client import get_http_client

# Bare (non-`with`) TestClient never runs the app's lifespan, so
# `app.state.http_client` (constructed there) does not exist -- exactly
# like gateway_service's own tests, the dependency is overridden directly
# rather than requiring a live database for lifespan's own readiness
# check (Phase 12 Batch 3: the orchestrator's tool adapters need a real
# client parameter; these HTTP-contract tests don't need it to reach a
# real service, since the default NullLLMProvider never calls a tool).
app.dependency_overrides[get_http_client] = lambda: httpx.AsyncClient(
    transport=httpx.MockTransport(lambda request: httpx.Response(404))
)

client = TestClient(app)


def test_minimal_valid_request_returns_200_with_honest_no_provider_answer():
    response = client.post("/api/v1/copilot/messages", json={"message": "What is happening in West region?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == (
        "Copilot's language model is not configured in this environment, so this request cannot be interpreted."
    )


def test_missing_message_is_rejected():
    response = client.post("/api/v1/copilot/messages", json={})

    assert response.status_code == 422


def test_invalid_workspace_is_rejected():
    response = client.post(
        "/api/v1/copilot/messages",
        json={"message": "hello", "workspace_context": {"workspace": "not-a-real-workspace"}},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "workspace", ["dashboard", "investigations", "recommendations", "analytics", "administration"]
)
def test_every_real_workspace_is_accepted(workspace):
    response = client.post(
        "/api/v1/copilot/messages",
        json={"message": "hello", "workspace_context": {"workspace": workspace}},
    )

    assert response.status_code == 200


def test_unknown_top_level_field_is_rejected():
    response = client.post("/api/v1/copilot/messages", json={"message": "hello", "unexpected_field": "value"})

    assert response.status_code == 422


def test_unknown_workspace_context_field_is_rejected():
    response = client.post(
        "/api/v1/copilot/messages",
        json={"message": "hello", "workspace_context": {"workspace": "dashboard", "region": "west"}},
    )

    assert response.status_code == 422


def test_supplied_conversation_id_is_echoed_unchanged():
    supplied = str(uuid.uuid4())

    response = client.post("/api/v1/copilot/messages", json={"message": "hello", "conversation_id": supplied})

    assert response.json()["conversation_id"] == supplied


def test_absent_conversation_id_generates_a_valid_uuid():
    response = client.post("/api/v1/copilot/messages", json={"message": "hello"})

    conversation_id = response.json()["conversation_id"]
    uuid.UUID(conversation_id)  # raises ValueError if not a valid UUID


def test_two_requests_without_a_conversation_id_get_different_ids():
    first = client.post("/api/v1/copilot/messages", json={"message": "hello"}).json()["conversation_id"]
    second = client.post("/api/v1/copilot/messages", json={"message": "hello"}).json()["conversation_id"]

    assert first != second


def test_response_shape_is_exactly_the_frozen_contract_no_more_no_less():
    response = client.post("/api/v1/copilot/messages", json={"message": "hello"})

    body = response.json()
    assert set(body.keys()) == {
        "answer",
        "key_findings",
        "evidence_references",
        "related_entities",
        "visualization_hint",
        "limitations",
        "conversation_id",
        "request_id",
    }


def test_evidence_findings_and_entities_are_empty_and_visualization_hint_is_omitted():
    response = client.post("/api/v1/copilot/messages", json={"message": "hello"})

    body = response.json()
    assert body["key_findings"] == []
    assert body["evidence_references"] == []
    assert body["related_entities"] == []
    assert body["visualization_hint"] is None


def test_limitations_honestly_state_no_llm_provider_is_configured():
    response = client.post("/api/v1/copilot/messages", json={"message": "hello"})

    limitations = response.json()["limitations"]
    assert len(limitations) == 1
    assert "No LLM provider is configured" in limitations[0]


def test_x_request_id_is_echoed_as_request_id():
    response = client.post(
        "/api/v1/copilot/messages",
        json={"message": "hello"},
        headers={"X-Request-ID": "test-request-id-123"},
    )

    assert response.headers["X-Request-ID"] == "test-request-id-123"
    assert response.json()["request_id"] == "test-request-id-123"


def test_health_readiness_and_metrics_are_unaffected_by_the_new_route():
    assert client.get("/health").status_code == 200
    assert client.get("/metrics").status_code == 200
    # /health/ready depends on a real database connection, which is not
    # necessarily available in this unit-test environment -- only assert
    # the route exists and returns a well-formed status, not a specific one.
    ready_response = client.get("/health/ready")
    assert ready_response.status_code in (200, 503)
    assert "status" in ready_response.json()
