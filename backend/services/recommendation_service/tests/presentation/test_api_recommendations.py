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
        incident_id="INC-DETAIL",
        generation_id=uuid.uuid4(),
    )
    record = saved[0]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
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
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/v1/recommendations/{uuid.uuid4()}")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_recommendation_by_id_422_for_malformed_uuid(wired_repository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/recommendations/not-a-uuid")

    assert response.status_code == 422


@pytest.mark.anyio
async def test_list_recommendations_returns_everything_by_default(wired_repository, make_recommendation):
    await wired_repository.save_many([make_recommendation(incident_id="INC-A")], incident_id="INC-A", generation_id=uuid.uuid4())
    await wired_repository.save_many([make_recommendation(incident_id="INC-B")], incident_id="INC-B", generation_id=uuid.uuid4())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/recommendations")

    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.anyio
async def test_list_recommendations_filters_by_category(wired_repository, make_recommendation):
    await wired_repository.save_many(
        [make_recommendation(category=RecommendationCategory.ESCALATE)], incident_id="INC-A", generation_id=uuid.uuid4()
    )
    await wired_repository.save_many(
        [make_recommendation(category=RecommendationCategory.MONITOR)], incident_id="INC-B", generation_id=uuid.uuid4()
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/recommendations", params={"category": "escalate"})

    results = response.json()
    assert len(results) == 1
    assert results[0]["category"] == "escalate"


@pytest.mark.anyio
async def test_list_recommendations_filters_by_priority(wired_repository, make_recommendation):
    await wired_repository.save_many(
        [make_recommendation(priority=RecommendationPriority.CRITICAL)], incident_id="INC-A", generation_id=uuid.uuid4()
    )
    await wired_repository.save_many(
        [make_recommendation(priority=RecommendationPriority.LOW)], incident_id="INC-B", generation_id=uuid.uuid4()
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/recommendations", params={"priority": "critical"})

    results = response.json()
    assert len(results) == 1
    assert results[0]["priority"] == "critical"


@pytest.mark.anyio
async def test_list_recommendations_summary_excludes_heavy_payload(wired_repository, make_recommendation):
    await wired_repository.save_many(
        [make_recommendation(rationale="Very long rationale.", priority_rationale="Very long priority rationale.")],
        incident_id="INC-SUMMARY",
        generation_id=uuid.uuid4(),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/recommendations")

    body = response.json()[0]
    assert "supporting_evidence" not in body
    assert "recommendation_rationale" not in body
    assert "priority_rationale" not in body
    assert set(body.keys()) == {
        "recommendation_id",
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
    await wired_repository.save_many([make_recommendation(incident_id="INC-A")], incident_id="INC-A", generation_id=uuid.uuid4())
    await wired_repository.save_many([make_recommendation(incident_id="INC-B")], incident_id="INC-B", generation_id=uuid.uuid4())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/incidents/INC-A/recommendations")

    results = response.json()
    assert len(results) == 1
    assert results[0]["incident_id"] == "INC-A"


@pytest.mark.anyio
async def test_get_latest_recommendations_for_incident(wired_repository, make_recommendation):
    await wired_repository.save_many(
        [make_recommendation(incident_id="INC-A", category=RecommendationCategory.MONITOR)],
        incident_id="INC-A",
        generation_id=uuid.uuid4(),
    )
    second_generation = uuid.uuid4()
    second = await wired_repository.save_many(
        [make_recommendation(incident_id="INC-A", category=RecommendationCategory.ESCALATE)],
        incident_id="INC-A",
        generation_id=second_generation,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/incidents/INC-A/recommendations/latest")

    results = response.json()
    assert len(results) == 1
    assert results[0]["recommendation_id"] == str(second[0].recommendation_id)
    assert results[0]["generation_id"] == str(second_generation)


@pytest.mark.anyio
async def test_get_latest_recommendations_returns_empty_list_when_none_exist(wired_repository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/incidents/INC-UNKNOWN/recommendations/latest")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_get_recommendations_by_generation(wired_repository, make_recommendation):
    generation_id = uuid.uuid4()
    saved = await wired_repository.save_many(
        [make_recommendation(), make_recommendation()], incident_id="INC-GEN", generation_id=generation_id
    )
    await wired_repository.save_many([make_recommendation()], incident_id="INC-OTHER", generation_id=uuid.uuid4())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/v1/recommendations/generations/{generation_id}")

    results = response.json()
    assert len(results) == 2
    assert {r["recommendation_id"] for r in results} == {str(record.recommendation_id) for record in saved}


@pytest.mark.anyio
async def test_get_statistics_aggregates_across_recommendations(wired_repository, make_recommendation):
    await wired_repository.save_many([make_recommendation(), make_recommendation()], incident_id="INC-A", generation_id=uuid.uuid4())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/recommendations/statistics")

    assert response.status_code == 200
    assert response.json()["total_count"] == 2


@pytest.mark.anyio
async def test_get_statistics_with_no_recommendations(wired_repository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/recommendations/statistics")

    body = response.json()
    assert body["total_count"] == 0
    assert body["category_counts"] == {}


@pytest.mark.anyio
async def test_no_write_endpoints_exist(wired_repository):
    """These APIs expose stored Recommendation artifacts only -- they never generate Recommendations."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        post_response = await client.post("/api/v1/recommendations", json={})
        put_response = await client.put(f"/api/v1/recommendations/{uuid.uuid4()}", json={})
        patch_response = await client.patch(f"/api/v1/recommendations/{uuid.uuid4()}", json={})
        delete_response = await client.delete(f"/api/v1/recommendations/{uuid.uuid4()}")

    assert post_response.status_code == 405
    assert put_response.status_code == 405
    assert patch_response.status_code == 405
    assert delete_response.status_code == 405
