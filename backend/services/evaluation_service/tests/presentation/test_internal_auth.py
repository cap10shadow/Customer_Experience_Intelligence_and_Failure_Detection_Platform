"""
Integration tests for internal service-to-service authentication on
evaluation_service's `/internal/events/business-impact-completed` route
(Phase 13 Batch 4, AD-5) -- the mirror of recommendation_service's own
`test_internal_auth.py`. Real FastAPI routes over HTTP (`ASGITransport`),
a fake consumer via `dependency_overrides` -- no database.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.services.evaluation_service.app.main import app
from backend.services.evaluation_service.app.presentation.dependencies import get_business_impact_completed_consumer
from backend.shared.config.settings import settings
from backend.shared.security.internal_auth import INTERNAL_SECRET_HEADER


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _FakeConsumeResult:
    def __init__(self):
        self.outcome = type("Outcome", (), {"value": "completed"})()
        self.evaluation_id = uuid.uuid4()
        self.reason = None


class _FakeConsumer:
    async def consume(self, raw_payload):
        return _FakeConsumeResult()


@pytest.fixture
def wired_consumer():
    consumer = _FakeConsumer()
    app.dependency_overrides[get_business_impact_completed_consumer] = lambda: consumer
    yield consumer
    app.dependency_overrides.clear()


async def _client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


@pytest.mark.anyio
async def test_internal_event_without_secret_is_rejected(wired_consumer):
    async with await _client() as client:
        response = await client.post("/internal/events/business-impact-completed", json={"event_id": "x"})

    assert response.status_code == 401


@pytest.mark.anyio
async def test_internal_event_with_wrong_secret_is_rejected(wired_consumer):
    async with await _client() as client:
        response = await client.post(
            "/internal/events/business-impact-completed",
            json={"event_id": "x"},
            headers={INTERNAL_SECRET_HEADER: "the-wrong-secret"},
        )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_internal_event_with_empty_secret_is_rejected(wired_consumer):
    async with await _client() as client:
        response = await client.post(
            "/internal/events/business-impact-completed",
            json={"event_id": "x"},
            headers={INTERNAL_SECRET_HEADER: ""},
        )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_internal_event_with_the_correct_secret_is_accepted(wired_consumer):
    async with await _client() as client:
        response = await client.post(
            "/internal/events/business-impact-completed",
            json={"event_id": "x"},
            headers={INTERNAL_SECRET_HEADER: settings.INTERNAL_SERVICE_SECRET},
        )

    assert response.status_code == 202
    assert response.json()["outcome"] == "completed"


@pytest.mark.anyio
async def test_internal_event_correlation_id_survives_the_auth_boundary(wired_consumer):
    async with await _client() as client:
        response = await client.post(
            "/internal/events/business-impact-completed",
            json={"event_id": "x"},
            headers={INTERNAL_SECRET_HEADER: settings.INTERNAL_SERVICE_SECRET, "X-Request-ID": "test-request-id-456"},
        )

    assert response.status_code == 202
    assert response.headers.get("X-Request-ID") == "test-request-id-456"


@pytest.mark.anyio
async def test_the_401_body_never_contains_the_configured_secret(wired_consumer):
    async with await _client() as client:
        response = await client.post("/internal/events/business-impact-completed", json={"event_id": "x"})

    assert settings.INTERNAL_SERVICE_SECRET not in response.text
