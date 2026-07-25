"""
API tests: the real FastAPI routes and real Pydantic response schemas,
exercised over HTTP with an in-memory FakeEvaluationRepository injected via
dependency_overrides. Read-only contract: no POST/PUT/PATCH/DELETE.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.services.evaluation_service.app.main import app
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


@pytest.mark.anyio
async def test_get_evaluation_by_id_returns_full_snapshot(wired_repository, make_evaluation):
    record = await wired_repository.save(make_evaluation())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/v1/evaluations/{record.evaluation_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["evaluation_id"] == str(record.evaluation_id)
    assert body["incident_id"] == record.evaluation.incident_id
    assert body["quality_assessment"]["quality_score"] == record.evaluation.quality_assessment.quality_score
    assert body["quality_assessment"]["quality_rating"] == record.evaluation.quality_assessment.quality_rating.value
    assert body["explainability_assessment"]["findings"] == list(record.evaluation.explainability_assessment.findings)
    assert body["confidence_summary"]["average_confidence"] == record.evaluation.confidence_summary.average_confidence
    assert body["validation_summary"]["is_valid"] is True
    assert body["root_cause_id"] is None
    assert body["business_impact_id"] is None


@pytest.mark.anyio
async def test_get_evaluation_by_id_404_when_missing(wired_repository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/v1/evaluations/{uuid.uuid4()}")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_evaluation_by_id_422_for_malformed_uuid(wired_repository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/evaluations/not-a-uuid")

    assert response.status_code == 422


@pytest.mark.anyio
async def test_list_evaluations_returns_everything_by_default(wired_repository, make_evaluation):
    await wired_repository.save(make_evaluation(incident_id="INC-A"))
    await wired_repository.save(make_evaluation(incident_id="INC-B"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/evaluations")

    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.anyio
async def test_list_evaluations_filters_by_incident_id(wired_repository, make_evaluation):
    await wired_repository.save(make_evaluation(incident_id="INC-A"))
    await wired_repository.save(make_evaluation(incident_id="INC-B"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/evaluations", params={"incident_id": "INC-A"})

    results = response.json()
    assert len(results) == 1
    assert results[0]["incident_id"] == "INC-A"


@pytest.mark.anyio
async def test_get_latest_evaluation_returns_the_most_recent(wired_repository, make_evaluation):
    await wired_repository.save(make_evaluation(incident_id="INC-A"))
    second = await wired_repository.save(make_evaluation(incident_id="INC-A"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/evaluations/latest/INC-A")

    assert response.status_code == 200
    assert response.json()["evaluation_id"] == str(second.evaluation_id)


@pytest.mark.anyio
async def test_get_latest_evaluation_404_when_none_exist(wired_repository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/evaluations/latest/INC-UNKNOWN")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_evaluation_history_returns_every_record_with_lineage(wired_repository, make_evaluation):
    first = await wired_repository.save(make_evaluation(incident_id="INC-A"))
    second = await wired_repository.save(make_evaluation(incident_id="INC-A"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/evaluations/history/INC-A")

    body = response.json()
    assert {item["evaluation_id"] for item in body} == {str(first.evaluation_id), str(second.evaluation_id)}
    second_entry = next(item for item in body if item["evaluation_id"] == str(second.evaluation_id))
    assert second_entry["previous_evaluation_id"] == str(first.evaluation_id)


@pytest.mark.anyio
async def test_get_statistics_aggregates_across_evaluations(wired_repository, make_evaluation):
    await wired_repository.save(make_evaluation())
    await wired_repository.save(make_evaluation())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/evaluations/statistics")

    assert response.status_code == 200
    assert response.json()["total_count"] == 2


@pytest.mark.anyio
async def test_get_statistics_with_no_evaluations(wired_repository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/evaluations/statistics")

    body = response.json()
    assert body["total_count"] == 0
    assert body["quality_rating_counts"] == {}


@pytest.mark.anyio
async def test_no_write_endpoints_exist(wired_repository):
    """These APIs expose stored Evaluation artifacts only -- they never execute evaluations."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        post_response = await client.post("/api/v1/evaluations", json={})
        put_response = await client.put(f"/api/v1/evaluations/{uuid.uuid4()}", json={})
        patch_response = await client.patch(f"/api/v1/evaluations/{uuid.uuid4()}", json={})
        delete_response = await client.delete(f"/api/v1/evaluations/{uuid.uuid4()}")

    assert post_response.status_code == 405
    assert put_response.status_code == 405
    assert patch_response.status_code == 405
    assert delete_response.status_code == 405
