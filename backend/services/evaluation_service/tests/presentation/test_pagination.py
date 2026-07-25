"""Pagination tests: defaults, explicit limit/offset, maximum-limit enforcement, invalid values -- for both collection endpoints (GET /evaluations and GET /evaluations/history/{incidentId})."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.services.evaluation_service.app.main import app
from backend.services.evaluation_service.app.presentation.api.evaluations import DEFAULT_LIMIT, MAX_LIMIT
from backend.services.evaluation_service.app.presentation.dependencies import get_evaluation_repository
from backend.services.evaluation_service.tests.fakes import FakeEvaluationRepository


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def wired_repository():
    repository = FakeEvaluationRepository()
    app.dependency_overrides[get_evaluation_repository] = lambda: repository
    yield repository
    app.dependency_overrides.clear()


async def _seed(repository, make_evaluation, count, incident_id="INC-PAGINATION"):
    for _ in range(count):
        await repository.save(make_evaluation(incident_id=incident_id))


@pytest.mark.anyio
async def test_list_evaluations_uses_a_sensible_default_limit(wired_repository, make_evaluation):
    await _seed(wired_repository, make_evaluation, DEFAULT_LIMIT + 5)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/evaluations")

    assert len(response.json()) == DEFAULT_LIMIT


@pytest.mark.anyio
async def test_list_evaluations_respects_explicit_limit_and_offset(wired_repository, make_evaluation):
    await _seed(wired_repository, make_evaluation, 5)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first_page = await client.get("/api/v1/evaluations", params={"limit": 2, "offset": 0})
        second_page = await client.get("/api/v1/evaluations", params={"limit": 2, "offset": 2})
        third_page = await client.get("/api/v1/evaluations", params={"limit": 2, "offset": 4})

    assert len(first_page.json()) == 2
    assert len(second_page.json()) == 2
    assert len(third_page.json()) == 1

    first_ids = {item["evaluation_id"] for item in first_page.json()}
    second_ids = {item["evaluation_id"] for item in second_page.json()}
    assert first_ids.isdisjoint(second_ids)


@pytest.mark.anyio
async def test_list_evaluations_enforces_maximum_limit(wired_repository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/evaluations", params={"limit": MAX_LIMIT + 1})

    assert response.status_code == 422


@pytest.mark.anyio
async def test_list_evaluations_allows_exactly_the_maximum_limit(wired_repository, make_evaluation):
    await _seed(wired_repository, make_evaluation, 3)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/evaluations", params={"limit": MAX_LIMIT})

    assert response.status_code == 200


@pytest.mark.anyio
async def test_list_evaluations_rejects_non_positive_limit(wired_repository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/evaluations", params={"limit": 0})

    assert response.status_code == 422


@pytest.mark.anyio
async def test_list_evaluations_rejects_negative_offset(wired_repository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/evaluations", params={"offset": -1})

    assert response.status_code == 422


@pytest.mark.anyio
async def test_evaluation_history_supports_pagination(wired_repository, make_evaluation):
    await _seed(wired_repository, make_evaluation, 5, incident_id="INC-HIST")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first_page = await client.get("/api/v1/evaluations/history/INC-HIST", params={"limit": 2, "offset": 0})
        second_page = await client.get("/api/v1/evaluations/history/INC-HIST", params={"limit": 2, "offset": 2})

    assert len(first_page.json()) == 2
    assert len(second_page.json()) == 2
    first_ids = {item["evaluation_id"] for item in first_page.json()}
    second_ids = {item["evaluation_id"] for item in second_page.json()}
    assert first_ids.isdisjoint(second_ids)


@pytest.mark.anyio
async def test_evaluation_history_enforces_maximum_limit(wired_repository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/evaluations/history/INC-HIST", params={"limit": MAX_LIMIT + 1})

    assert response.status_code == 422
