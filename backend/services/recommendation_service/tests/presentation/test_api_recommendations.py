"""
API tests: the real FastAPI routes and real Pydantic response schemas,
exercised over HTTP with an in-memory FakeRecommendationRepository injected
via dependency_overrides. Read-only contract: no POST/PUT/PATCH/DELETE.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.main import app
from backend.services.recommendation_service.app.presentation.dependencies import get_recommendation_repository
from backend.services.recommendation_service.tests.fakes import FakeRecommendationRepository
from backend.shared.config.settings import settings
from backend.shared.security.internal_auth import INTERNAL_SECRET_HEADER

# Phase 13 Batch 4 (AD-5): the PATCH .../decision route in this file now
# requires the internal-service credential; applied to every client
# here (GET routes ignore it -- harmless, and keeps this file's own
# client-construction pattern uniform).
_INTERNAL_AUTH_HEADERS = {INTERNAL_SECRET_HEADER: settings.INTERNAL_SERVICE_SECRET}

DATASET_ID = uuid.uuid4()
DATASET_VERSION_ID = uuid.uuid4()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def wired_repository():
    repository = FakeRecommendationRepository()
    app.dependency_overrides[get_recommendation_repository] = lambda: repository
    yield repository
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_get_recommendation_by_id_returns_full_detail(wired_repository, make_recommendation):
    saved = await wired_repository.save_many(
        [
            make_recommendation(
                incident_id="INC-DETAIL", rationale="Full rationale text.", priority_rationale="Full priority rationale text."
            )
        ],
        dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-DETAIL",
        generation_id=uuid.uuid4(),
    )
    record = saved[0]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        response = await client.get(f"/api/v1/recommendations/{record.recommendation_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["recommendation_id"] == str(record.recommendation_id)
    assert body["incident_id"] == "INC-DETAIL"
    assert body["generation_id"] == str(record.generation_id)
    assert body["recommendation_rationale"] == "Full rationale text."
    assert body["priority_rationale"] == "Full priority rationale text."
    assert body["supporting_evidence"] == [
        {"source": e.source.value, "description": e.description, "weight": e.weight}
        for e in record.recommendation.supporting_evidence
    ]


@pytest.mark.anyio
async def test_get_recommendation_by_id_404_when_missing(wired_repository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        response = await client.get(f"/api/v1/recommendations/{uuid.uuid4()}")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_recommendation_by_id_422_for_malformed_uuid(wired_repository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        response = await client.get("/api/v1/recommendations/not-a-uuid")

    assert response.status_code == 422


@pytest.mark.anyio
async def test_list_recommendations_returns_everything_by_default(wired_repository, make_recommendation):
    await wired_repository.save_many([make_recommendation(incident_id="INC-A")], dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-A", generation_id=uuid.uuid4())
    await wired_repository.save_many([make_recommendation(incident_id="INC-B")], dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-B", generation_id=uuid.uuid4())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        response = await client.get("/api/v1/recommendations")

    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.anyio
async def test_list_recommendations_filters_by_category(wired_repository, make_recommendation):
    await wired_repository.save_many(
        [make_recommendation(category=RecommendationCategory.ESCALATE)], dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-A", generation_id=uuid.uuid4()
    )
    await wired_repository.save_many(
        [make_recommendation(category=RecommendationCategory.MONITOR)], dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-B", generation_id=uuid.uuid4()
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        response = await client.get("/api/v1/recommendations", params={"category": "escalate"})

    results = response.json()
    assert len(results) == 1
    assert results[0]["category"] == "escalate"


@pytest.mark.anyio
async def test_list_recommendations_filters_by_priority(wired_repository, make_recommendation):
    await wired_repository.save_many(
        [make_recommendation(priority=RecommendationPriority.CRITICAL)], dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-A", generation_id=uuid.uuid4()
    )
    await wired_repository.save_many(
        [make_recommendation(priority=RecommendationPriority.LOW)], dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-B", generation_id=uuid.uuid4()
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        response = await client.get("/api/v1/recommendations", params={"priority": "critical"})

    results = response.json()
    assert len(results) == 1
    assert results[0]["priority"] == "critical"


@pytest.mark.anyio
async def test_list_recommendations_summary_excludes_heavy_payload(wired_repository, make_recommendation):
    await wired_repository.save_many(
        [make_recommendation(rationale="Very long rationale.", priority_rationale="Very long priority rationale.")],
        dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-SUMMARY",
        generation_id=uuid.uuid4(),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        response = await client.get("/api/v1/recommendations")

    body = response.json()[0]
    assert "supporting_evidence" not in body
    assert "recommendation_rationale" not in body
    assert "priority_rationale" not in body
    assert set(body.keys()) == {
        "recommendation_id",
        "dataset_id",
        "dataset_version_id",
        "incident_id",
        "generation_id",
        "category",
        "priority",
        "score",
        "action",
        "created_at",
    }


@pytest.mark.anyio
async def test_get_recommendations_for_incident(wired_repository, make_recommendation):
    await wired_repository.save_many([make_recommendation(incident_id="INC-A")], dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-A", generation_id=uuid.uuid4())
    await wired_repository.save_many([make_recommendation(incident_id="INC-B")], dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-B", generation_id=uuid.uuid4())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        response = await client.get("/api/v1/incidents/INC-A/recommendations")

    results = response.json()
    assert len(results) == 1
    assert results[0]["incident_id"] == "INC-A"


@pytest.mark.anyio
async def test_get_latest_recommendations_for_incident(wired_repository, make_recommendation):
    await wired_repository.save_many(
        [make_recommendation(incident_id="INC-A", category=RecommendationCategory.MONITOR)],
        dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-A",
        generation_id=uuid.uuid4(),
    )
    second_generation = uuid.uuid4()
    second = await wired_repository.save_many(
        [make_recommendation(incident_id="INC-A", category=RecommendationCategory.ESCALATE)],
        dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-A",
        generation_id=second_generation,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        response = await client.get("/api/v1/incidents/INC-A/recommendations/latest")

    results = response.json()
    assert len(results) == 1
    assert results[0]["recommendation_id"] == str(second[0].recommendation_id)
    assert results[0]["generation_id"] == str(second_generation)


@pytest.mark.anyio
async def test_get_latest_recommendations_returns_empty_list_when_none_exist(wired_repository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        response = await client.get("/api/v1/incidents/INC-UNKNOWN/recommendations/latest")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_get_recommendations_by_generation(wired_repository, make_recommendation):
    generation_id = uuid.uuid4()
    saved = await wired_repository.save_many(
        [make_recommendation(), make_recommendation()], dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-GEN", generation_id=generation_id
    )
    await wired_repository.save_many([make_recommendation()], dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-OTHER", generation_id=uuid.uuid4())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        response = await client.get(f"/api/v1/recommendations/generations/{generation_id}")

    results = response.json()
    assert len(results) == 2
    assert {r["recommendation_id"] for r in results} == {str(record.recommendation_id) for record in saved}


@pytest.mark.anyio
async def test_get_statistics_aggregates_across_recommendations(wired_repository, make_recommendation):
    await wired_repository.save_many([make_recommendation(), make_recommendation()], dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-A", generation_id=uuid.uuid4())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        response = await client.get("/api/v1/recommendations/statistics")

    assert response.status_code == 200
    assert response.json()["total_count"] == 2


@pytest.mark.anyio
async def test_get_statistics_with_no_recommendations(wired_repository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        response = await client.get("/api/v1/recommendations/statistics")

    body = response.json()
    assert body["total_count"] == 0
    assert body["category_counts"] == {}


@pytest.mark.anyio
async def test_no_write_endpoints_exist(wired_repository):
    """
    These APIs expose stored Recommendation artifacts only -- they never
    generate Recommendations, and never mutate a Recommendation's own
    fields. The one deliberate exception is the decision sub-resource
    (`PATCH /recommendations/{id}/decision`, Step 7.X G-01, tested
    separately below) -- PATCH directly against the Recommendation
    resource itself remains unsupported.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        post_response = await client.post("/api/v1/recommendations", json={})
        put_response = await client.put(f"/api/v1/recommendations/{uuid.uuid4()}", json={})
        patch_response = await client.patch(f"/api/v1/recommendations/{uuid.uuid4()}", json={})
        delete_response = await client.delete(f"/api/v1/recommendations/{uuid.uuid4()}")

    assert post_response.status_code == 405
    assert put_response.status_code == 405
    assert patch_response.status_code == 405
    assert delete_response.status_code == 405


@pytest.mark.anyio
async def test_get_recommendation_by_id_exposes_null_decision_fields_when_never_decided(wired_repository, make_recommendation):
    saved = await wired_repository.save_many([make_recommendation()], dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-A", generation_id=uuid.uuid4())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        response = await client.get(f"/api/v1/recommendations/{saved[0].recommendation_id}")

    body = response.json()
    assert body["decision"] is None
    assert body["decision_note"] is None
    assert body["decided_at"] is None


@pytest.mark.anyio
async def test_patch_decision_persists_and_get_reflects_it(wired_repository, make_recommendation):
    saved = await wired_repository.save_many([make_recommendation()], dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-A", generation_id=uuid.uuid4())
    recommendation_id = saved[0].recommendation_id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        patch_response = await client.patch(
            f"/api/v1/recommendations/{recommendation_id}/decision",
            json={"decision": "approved", "note": "Looks correct."},
        )
        assert patch_response.status_code == 200
        patched_body = patch_response.json()
        assert patched_body["decision"] == "approved"
        assert patched_body["decision_note"] == "Looks correct."
        assert patched_body["decided_at"] is not None

        get_response = await client.get(f"/api/v1/recommendations/{recommendation_id}")

    get_body = get_response.json()
    assert get_body["decision"] == "approved"
    assert get_body["decision_note"] == "Looks correct."
    assert get_body["decided_at"] == patched_body["decided_at"]


@pytest.mark.anyio
async def test_patch_decision_without_note_is_valid(wired_repository, make_recommendation):
    saved = await wired_repository.save_many([make_recommendation()], dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-A", generation_id=uuid.uuid4())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        response = await client.patch(
            f"/api/v1/recommendations/{saved[0].recommendation_id}/decision", json={"decision": "deferred"}
        )

    assert response.status_code == 200
    assert response.json()["decision_note"] is None


@pytest.mark.anyio
async def test_patch_decision_rejects_invalid_decision_value(wired_repository, make_recommendation):
    saved = await wired_repository.save_many([make_recommendation()], dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-A", generation_id=uuid.uuid4())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        response = await client.patch(
            f"/api/v1/recommendations/{saved[0].recommendation_id}/decision", json={"decision": "maybe"}
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_patch_decision_404_when_recommendation_missing(wired_repository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        response = await client.patch(
            f"/api/v1/recommendations/{uuid.uuid4()}/decision", json={"decision": "approved"}
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_patch_decision_repeated_calls_overwrite_deterministically(wired_repository, make_recommendation):
    saved = await wired_repository.save_many([make_recommendation()], dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-A", generation_id=uuid.uuid4())
    recommendation_id = saved[0].recommendation_id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        first = await client.patch(
            f"/api/v1/recommendations/{recommendation_id}/decision",
            json={"decision": "approved", "note": "First pass."},
        )
        second = await client.patch(
            f"/api/v1/recommendations/{recommendation_id}/decision",
            json={"decision": "deferred", "note": "Changed my mind."},
        )

    assert first.json()["decision"] == "approved"
    assert second.json()["decision"] == "deferred"
    assert second.json()["decision_note"] == "Changed my mind."


@pytest.mark.anyio
async def test_patch_decision_never_alters_recommendation_id_or_incident_id(wired_repository, make_recommendation):
    saved = await wired_repository.save_many(
        [make_recommendation(incident_id="INC-IDENTITY")], dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-IDENTITY", generation_id=uuid.uuid4()
    )
    recommendation_id = saved[0].recommendation_id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        response = await client.patch(
            f"/api/v1/recommendations/{recommendation_id}/decision", json={"decision": "approved"}
        )

    body = response.json()
    assert body["recommendation_id"] == str(recommendation_id)
    assert body["incident_id"] == "INC-IDENTITY"


@pytest.mark.anyio
async def test_patch_decision_response_never_exposes_actor_or_owner_fields(wired_repository, make_recommendation):
    saved = await wired_repository.save_many([make_recommendation()], dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-A", generation_id=uuid.uuid4())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        response = await client.patch(
            f"/api/v1/recommendations/{saved[0].recommendation_id}/decision", json={"decision": "approved"}
        )

    body = response.json()
    for forbidden_field in ("actor_id", "user_id", "owner", "approval_authority", "lifecycle_stage", "decided_by"):
        assert forbidden_field not in body
