"""Pagination tests: defaults, explicit limit/offset, maximum-limit enforcement, invalid values -- across every collection endpoint."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.services.recommendation_service.app.main import app
from backend.services.recommendation_service.app.presentation.api.recommendations import DEFAULT_LIMIT, MAX_LIMIT
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


DATASET_ID = uuid.uuid4()
DATASET_VERSION_ID = uuid.uuid4()


async def _seed(repository, make_recommendation, count, incident_id="INC-PAGINATION"):
    recommendations = [make_recommendation(incident_id=incident_id) for _ in range(count)]
    await repository.save_many(recommendations, dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id=incident_id, generation_id=uuid.uuid4())


@pytest.mark.anyio
async def test_list_recommendations_uses_a_sensible_default_limit(wired_repository, make_recommendation):
    await _seed(wired_repository, make_recommendation, DEFAULT_LIMIT + 5)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/recommendations")

    assert len(response.json()) == DEFAULT_LIMIT


@pytest.mark.anyio
async def test_list_recommendations_respects_explicit_limit_and_offset(wired_repository, make_recommendation):
    await _seed(wired_repository, make_recommendation, 5)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first_page = await client.get("/api/v1/recommendations", params={"limit": 2, "offset": 0})
        second_page = await client.get("/api/v1/recommendations", params={"limit": 2, "offset": 2})
        third_page = await client.get("/api/v1/recommendations", params={"limit": 2, "offset": 4})

    assert len(first_page.json()) == 2
    assert len(second_page.json()) == 2
    assert len(third_page.json()) == 1
    first_ids = {item["recommendation_id"] for item in first_page.json()}
    second_ids = {item["recommendation_id"] for item in second_page.json()}
    assert first_ids.isdisjoint(second_ids)


@pytest.mark.anyio
async def test_list_recommendations_enforces_maximum_limit(wired_repository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/recommendations", params={"limit": MAX_LIMIT + 1})

    assert response.status_code == 422


@pytest.mark.anyio
async def test_list_recommendations_allows_exactly_the_maximum_limit(wired_repository, make_recommendation):
    await _seed(wired_repository, make_recommendation, 3)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/recommendations", params={"limit": MAX_LIMIT})

    assert response.status_code == 200


@pytest.mark.anyio
async def test_list_recommendations_rejects_non_positive_limit(wired_repository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/recommendations", params={"limit": 0})

    assert response.status_code == 422


@pytest.mark.anyio
async def test_list_recommendations_rejects_negative_offset(wired_repository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/recommendations", params={"offset": -1})

    assert response.status_code == 422


@pytest.mark.anyio
async def test_incident_recommendations_supports_pagination(wired_repository, make_recommendation):
    await _seed(wired_repository, make_recommendation, 5, incident_id="INC-HIST")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first_page = await client.get("/api/v1/incidents/INC-HIST/recommendations", params={"limit": 2, "offset": 0})
        second_page = await client.get("/api/v1/incidents/INC-HIST/recommendations", params={"limit": 2, "offset": 2})

    assert len(first_page.json()) == 2
    assert len(second_page.json()) == 2
    first_ids = {item["recommendation_id"] for item in first_page.json()}
    second_ids = {item["recommendation_id"] for item in second_page.json()}
    assert first_ids.isdisjoint(second_ids)


@pytest.mark.anyio
async def test_incident_recommendations_enforces_maximum_limit(wired_repository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/incidents/INC-HIST/recommendations", params={"limit": MAX_LIMIT + 1})

    assert response.status_code == 422


@pytest.mark.anyio
async def test_generation_recommendations_supports_pagination(wired_repository, make_recommendation):
    generation_id = uuid.uuid4()
    recommendations = [make_recommendation(incident_id="INC-GEN") for _ in range(5)]
    await wired_repository.save_many(recommendations, dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-GEN", generation_id=generation_id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first_page = await client.get(f"/api/v1/recommendations/generations/{generation_id}", params={"limit": 2, "offset": 0})
        second_page = await client.get(f"/api/v1/recommendations/generations/{generation_id}", params={"limit": 2, "offset": 2})

    assert len(first_page.json()) == 2
    assert len(second_page.json()) == 2
