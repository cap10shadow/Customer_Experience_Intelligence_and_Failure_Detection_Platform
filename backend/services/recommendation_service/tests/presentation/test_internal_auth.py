"""
Integration tests for internal service-to-service authentication on
recommendation_service (Phase 13 Batch 4, AD-5): the
`/internal/events/business-impact-completed` route and the
`PATCH /recommendations/{id}/decision` route, both now genuine internal
mutation boundaries requiring `X-Internal-Secret`. Real FastAPI routes
over HTTP (`ASGITransport`), an in-memory fake repository/consumer via
`dependency_overrides` -- no database.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.services.recommendation_service.app.main import app
from backend.services.recommendation_service.app.presentation.dependencies import (
    get_business_impact_completed_consumer,
    get_recommendation_repository,
)
from backend.services.recommendation_service.tests.fakes import FakeRecommendationRepository
from backend.shared.config.settings import settings
from backend.shared.security.internal_auth import INTERNAL_SECRET_HEADER, PRINCIPAL_USER_ID_HEADER


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def wired_repository():
    repository = FakeRecommendationRepository()
    app.dependency_overrides[get_recommendation_repository] = lambda: repository
    yield repository
    app.dependency_overrides.clear()


class _FakeConsumeResult:
    def __init__(self):
        self.outcome = type("Outcome", (), {"value": "completed"})()
        self.generation_id = uuid.uuid4()
        self.recommendation_count = 0
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


# --- /internal/events/business-impact-completed --------------------------------------


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
            headers={INTERNAL_SECRET_HEADER: settings.INTERNAL_SERVICE_SECRET, "X-Request-ID": "test-request-id-123"},
        )

    assert response.status_code == 202
    assert response.headers.get("X-Request-ID") == "test-request-id-123"


@pytest.mark.anyio
async def test_the_401_body_never_contains_the_configured_secret(wired_consumer):
    async with await _client() as client:
        response = await client.post("/internal/events/business-impact-completed", json={"event_id": "x"})

    assert settings.INTERNAL_SERVICE_SECRET not in response.text


# --- PATCH /recommendations/{id}/decision ---------------------------------------------


@pytest.mark.anyio
async def test_decision_patch_without_secret_is_rejected(wired_repository, make_recommendation):
    saved = await wired_repository.save_many(
        [make_recommendation(incident_id="INC-1")], incident_id="INC-1", generation_id=uuid.uuid4()
    )
    async with await _client() as client:
        response = await client.patch(
            f"/api/v1/recommendations/{saved[0].recommendation_id}/decision", json={"decision": "approved"}
        )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_decision_patch_with_the_correct_secret_succeeds(wired_repository, make_recommendation):
    saved = await wired_repository.save_many(
        [make_recommendation(incident_id="INC-2")], incident_id="INC-2", generation_id=uuid.uuid4()
    )
    async with await _client() as client:
        response = await client.patch(
            f"/api/v1/recommendations/{saved[0].recommendation_id}/decision",
            json={"decision": "approved"},
            headers={INTERNAL_SECRET_HEADER: settings.INTERNAL_SERVICE_SECRET},
        )

    assert response.status_code == 200
    assert response.json()["decision"] == "approved"


@pytest.mark.anyio
async def test_decision_patch_accepts_the_gateway_attested_principal_header_without_changing_the_response(
    wired_repository, make_recommendation
):
    """Phase 13 Batch 4: the principal header is accepted/logged only -- no `decided_by` field exists on the response yet (that is explicitly a later batch's scope)."""
    saved = await wired_repository.save_many(
        [make_recommendation(incident_id="INC-3")], incident_id="INC-3", generation_id=uuid.uuid4()
    )
    async with await _client() as client:
        response = await client.patch(
            f"/api/v1/recommendations/{saved[0].recommendation_id}/decision",
            json={"decision": "rejected"},
            headers={
                INTERNAL_SECRET_HEADER: settings.INTERNAL_SERVICE_SECRET,
                PRINCIPAL_USER_ID_HEADER: str(uuid.uuid4()),
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert "decided_by" not in body
    assert "decidedBy" not in body
