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
    """Phase 13 Batch 4/5: the principal header is now persisted (decided_by/actor_id) -- but never exposed on this response, AD-3 requiring no such API contract."""
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


# --- Phase 13 Batch 5 (AD-3): recommendation decision attribution and history ----------


@pytest.mark.anyio
async def test_decision_patch_persists_the_gateway_attested_principal_as_decided_by(
    wired_repository, make_recommendation
):
    saved = await wired_repository.save_many(
        [make_recommendation(incident_id="INC-ATTR-1")], incident_id="INC-ATTR-1", generation_id=uuid.uuid4()
    )
    actor_id = uuid.uuid4()

    async with await _client() as client:
        response = await client.patch(
            f"/api/v1/recommendations/{saved[0].recommendation_id}/decision",
            json={"decision": "approved"},
            headers={INTERNAL_SECRET_HEADER: settings.INTERNAL_SERVICE_SECRET, PRINCIPAL_USER_ID_HEADER: str(actor_id)},
        )

    assert response.status_code == 200
    updated = await wired_repository.get_by_id(saved[0].recommendation_id)
    assert updated is not None
    assert updated.decided_by == actor_id


@pytest.mark.anyio
async def test_decision_patch_without_principal_header_persists_no_known_actor(wired_repository, make_recommendation):
    saved = await wired_repository.save_many(
        [make_recommendation(incident_id="INC-ATTR-2")], incident_id="INC-ATTR-2", generation_id=uuid.uuid4()
    )

    async with await _client() as client:
        response = await client.patch(
            f"/api/v1/recommendations/{saved[0].recommendation_id}/decision",
            json={"decision": "approved"},
            headers={INTERNAL_SECRET_HEADER: settings.INTERNAL_SERVICE_SECRET},
        )

    assert response.status_code == 200
    updated = await wired_repository.get_by_id(saved[0].recommendation_id)
    assert updated is not None
    assert updated.decided_by is None


@pytest.mark.anyio
async def test_decision_patch_malformed_principal_header_persists_no_known_actor_and_still_succeeds(
    wired_repository, make_recommendation
):
    """A malformed X-Authenticated-User-Id (not a valid UUID) never fails the request or fabricates an actor -- it degrades to 'no known actor', same as a missing header."""
    saved = await wired_repository.save_many(
        [make_recommendation(incident_id="INC-ATTR-3")], incident_id="INC-ATTR-3", generation_id=uuid.uuid4()
    )

    async with await _client() as client:
        response = await client.patch(
            f"/api/v1/recommendations/{saved[0].recommendation_id}/decision",
            json={"decision": "approved"},
            headers={INTERNAL_SECRET_HEADER: settings.INTERNAL_SERVICE_SECRET, PRINCIPAL_USER_ID_HEADER: "not-a-uuid"},
        )

    assert response.status_code == 200
    updated = await wired_repository.get_by_id(saved[0].recommendation_id)
    assert updated is not None
    assert updated.decided_by is None


@pytest.mark.anyio
async def test_decision_patch_ignores_any_client_supplied_actor_field_in_the_request_body(
    wired_repository, make_recommendation
):
    """The request schema declares no actor/owner field at all -- a client attempting to spoof attribution via the body is structurally ignored, and the real actor still comes only from the trusted header."""
    saved = await wired_repository.save_many(
        [make_recommendation(incident_id="INC-ATTR-4")], incident_id="INC-ATTR-4", generation_id=uuid.uuid4()
    )
    real_actor_id = uuid.uuid4()
    spoofed_actor_id = uuid.uuid4()

    async with await _client() as client:
        response = await client.patch(
            f"/api/v1/recommendations/{saved[0].recommendation_id}/decision",
            json={"decision": "approved", "decided_by": str(spoofed_actor_id), "actor_id": str(spoofed_actor_id), "user_id": str(spoofed_actor_id)},
            headers={
                INTERNAL_SECRET_HEADER: settings.INTERNAL_SERVICE_SECRET,
                PRINCIPAL_USER_ID_HEADER: str(real_actor_id),
            },
        )

    assert response.status_code == 200
    updated = await wired_repository.get_by_id(saved[0].recommendation_id)
    assert updated is not None
    assert updated.decided_by == real_actor_id
    assert updated.decided_by != spoofed_actor_id


@pytest.mark.anyio
async def test_decision_patch_creates_a_history_record_with_the_correct_recommendation_decision_and_actor(
    wired_repository, make_recommendation
):
    saved = await wired_repository.save_many(
        [make_recommendation(incident_id="INC-HIST-1")], incident_id="INC-HIST-1", generation_id=uuid.uuid4()
    )
    recommendation_id = saved[0].recommendation_id
    actor_id = uuid.uuid4()

    async with await _client() as client:
        response = await client.patch(
            f"/api/v1/recommendations/{recommendation_id}/decision",
            json={"decision": "deferred", "note": "Needs more evidence."},
            headers={INTERNAL_SECRET_HEADER: settings.INTERNAL_SERVICE_SECRET, PRINCIPAL_USER_ID_HEADER: str(actor_id)},
        )

    assert response.status_code == 200
    assert len(wired_repository.decision_history) == 1
    history_row = wired_repository.decision_history[0]
    assert history_row["recommendation_id"] == recommendation_id
    assert history_row["decision"].value == "deferred"
    assert history_row["decision_note"] == "Needs more evidence."
    assert history_row["actor_id"] == actor_id
    assert history_row["created_at"] is not None


@pytest.mark.anyio
async def test_decision_patch_repeated_calls_each_append_their_own_history_record(wired_repository, make_recommendation):
    saved = await wired_repository.save_many(
        [make_recommendation(incident_id="INC-HIST-2")], incident_id="INC-HIST-2", generation_id=uuid.uuid4()
    )
    recommendation_id = saved[0].recommendation_id
    first_actor = uuid.uuid4()
    second_actor = uuid.uuid4()

    async with await _client() as client:
        await client.patch(
            f"/api/v1/recommendations/{recommendation_id}/decision",
            json={"decision": "approved"},
            headers={INTERNAL_SECRET_HEADER: settings.INTERNAL_SERVICE_SECRET, PRINCIPAL_USER_ID_HEADER: str(first_actor)},
        )
        await client.patch(
            f"/api/v1/recommendations/{recommendation_id}/decision",
            json={"decision": "rejected"},
            headers={INTERNAL_SECRET_HEADER: settings.INTERNAL_SERVICE_SECRET, PRINCIPAL_USER_ID_HEADER: str(second_actor)},
        )

    assert len(wired_repository.decision_history) == 2
    assert wired_repository.decision_history[0]["actor_id"] == first_actor
    assert wired_repository.decision_history[1]["actor_id"] == second_actor
