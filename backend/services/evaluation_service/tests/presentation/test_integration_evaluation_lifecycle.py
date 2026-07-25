"""
Integration test: CompletedIntelligence -> EvaluationOrchestrator (real,
frozen Step 1 engines) -> EvaluationRepository.save() -> REST API read-back.
Proves every field computed by the domain engines survives, unchanged, all
the way through persistence to the JSON response -- the full Step 2
workflow end to end.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.services.evaluation_service.app.application.evaluation_orchestrator import EvaluationOrchestrator
from backend.services.evaluation_service.app.domain.confidence_analyzer import ConfidenceAnalyzer
from backend.services.evaluation_service.app.domain.evaluation_builder import EvaluationBuilder
from backend.services.evaluation_service.app.domain.evaluation_record import EvaluationRecord
from backend.services.evaluation_service.app.domain.explainability_engine import ExplainabilityEngine
from backend.services.evaluation_service.app.domain.quality_engine import QualityEngine
from backend.services.evaluation_service.app.domain.validation_engine import ValidationEngine
from backend.services.evaluation_service.app.domain.validation_summary import ValidationSummary
from backend.services.evaluation_service.app.main import app
from backend.services.evaluation_service.app.presentation.dependencies import get_evaluation_repository
from backend.services.evaluation_service.tests.fakes import FakeEvaluationRepository


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _orchestrator(repository: FakeEvaluationRepository) -> EvaluationOrchestrator:
    return EvaluationOrchestrator(
        validation_engine=ValidationEngine(),
        quality_engine=QualityEngine(),
        explainability_engine=ExplainabilityEngine(),
        confidence_analyzer=ConfidenceAnalyzer(),
        evaluation_builder=EvaluationBuilder(),
        repository=repository,
    )


@pytest.mark.anyio
async def test_full_lifecycle_engine_to_persistence_to_api(make_completed_intelligence):
    repository = FakeEvaluationRepository()
    orchestrator = _orchestrator(repository)

    completed_intelligence = make_completed_intelligence()
    persisted = await orchestrator.evaluate(completed_intelligence)
    assert isinstance(persisted, EvaluationRecord)

    app.dependency_overrides[get_evaluation_repository] = lambda: repository
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(f"/api/v1/evaluations/{persisted.evaluation_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["evaluation_id"] == str(persisted.evaluation_id)
    assert body["incident_id"] == completed_intelligence.incident_id
    assert body["evaluation_version"] == persisted.evaluation.metadata.evaluation_version
    assert body["quality_assessment"]["quality_score"] == persisted.evaluation.quality_assessment.quality_score
    assert body["quality_assessment"]["quality_rating"] == persisted.evaluation.quality_assessment.quality_rating.value
    assert body["quality_assessment"]["findings"] == list(persisted.evaluation.quality_assessment.findings)
    assert (
        body["explainability_assessment"]["explainability_score"]
        == persisted.evaluation.explainability_assessment.explainability_score
    )
    assert (
        body["confidence_summary"]["average_confidence"] == persisted.evaluation.confidence_summary.average_confidence
    )
    assert body["validation_summary"]["is_valid"] is True


@pytest.mark.anyio
async def test_full_lifecycle_is_reachable_via_the_list_and_latest_endpoints(make_completed_intelligence):
    repository = FakeEvaluationRepository()
    orchestrator = _orchestrator(repository)
    completed_intelligence = make_completed_intelligence()

    persisted = await orchestrator.evaluate(completed_intelligence)

    app.dependency_overrides[get_evaluation_repository] = lambda: repository
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            list_response = await client.get(
                "/api/v1/evaluations", params={"incident_id": completed_intelligence.incident_id}
            )
            latest_response = await client.get(f"/api/v1/evaluations/latest/{completed_intelligence.incident_id}")
    finally:
        app.dependency_overrides.clear()

    assert len(list_response.json()) == 1
    assert list_response.json()[0]["evaluation_id"] == str(persisted.evaluation_id)
    assert latest_response.status_code == 200
    assert latest_response.json()["evaluation_id"] == str(persisted.evaluation_id)


@pytest.mark.anyio
async def test_full_lifecycle_validation_failure_never_reaches_persistence_or_the_api(make_completed_intelligence):
    repository = FakeEvaluationRepository()
    orchestrator = _orchestrator(repository)

    result = await orchestrator.evaluate(make_completed_intelligence(incident_id=""))

    assert isinstance(result, ValidationSummary)
    assert not isinstance(result, EvaluationRecord)
    assert repository.by_id == {}

    app.dependency_overrides[get_evaluation_repository] = lambda: repository
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/evaluations")
    finally:
        app.dependency_overrides.clear()

    assert response.json() == []


@pytest.mark.anyio
async def test_repeated_evaluations_for_the_same_incident_are_all_visible_through_history(make_completed_intelligence):
    repository = FakeEvaluationRepository()
    orchestrator = _orchestrator(repository)
    completed_intelligence = make_completed_intelligence()

    first = await orchestrator.evaluate(completed_intelligence)
    second = await orchestrator.evaluate(completed_intelligence)

    app.dependency_overrides[get_evaluation_repository] = lambda: repository
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(f"/api/v1/evaluations/history/{completed_intelligence.incident_id}")
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert {item["evaluation_id"] for item in body} == {str(first.evaluation_id), str(second.evaluation_id)}
