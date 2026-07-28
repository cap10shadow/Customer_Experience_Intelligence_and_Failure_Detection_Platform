"""
Integration tests for the Phase 8 Step 3 execution lifecycle, exercised
over real HTTP against the actual FastAPI app: BusinessImpactCompleted ->
Event Consumer -> EvaluationLifecycleService -> EvaluationOrchestrator ->
Domain -> Repository -> EvaluationCompleted.

Uses FakeEvaluationRepository (in-memory) wired behind the real
BusinessImpactCompletedConsumer/EvaluationLifecycleService/EvaluationOrchestrator,
via `app.dependency_overrides` on `get_business_impact_completed_consumer` --
the same dependency-override pattern the Step 2 API tests already use for
`get_evaluation_repository`. Genuine concurrent-duplicate-processing
protection (the database UNIQUE constraint racing two real transactions)
is covered separately, against real PostgreSQL, in
test_postgresql_evaluation_repository.py -- an in-memory Fake has no real
transaction isolation to prove that guarantee with.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.services.evaluation_service.app.application.evaluation_orchestrator import EvaluationOrchestrator
from backend.services.evaluation_service.app.application.lifecycle.evaluation_lifecycle_service import (
    EvaluationLifecycleService,
)
from backend.services.evaluation_service.app.application.ports.event_publisher import EventPublisher
from backend.services.evaluation_service.app.domain.confidence_analyzer import ConfidenceAnalyzer
from backend.services.evaluation_service.app.domain.evaluation_builder import EvaluationBuilder
from backend.services.evaluation_service.app.domain.explainability_engine import ExplainabilityEngine
from backend.services.evaluation_service.app.domain.quality_engine import QualityEngine
from backend.services.evaluation_service.app.domain.validation_engine import ValidationEngine
from backend.services.evaluation_service.app.infrastructure.messaging.consumers.business_impact_completed_consumer import (
    BusinessImpactCompletedConsumer,
)
from backend.services.evaluation_service.app.main import app
from backend.services.evaluation_service.app.presentation.dependencies import (
    get_business_impact_completed_consumer,
    get_evaluation_repository,
)
from backend.services.evaluation_service.tests.fakes import FakeEvaluationRepository


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _FakeSession:
    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass


class _RecordingEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self.published = []

    async def publish(self, event) -> None:
        self.published.append(event)


class _FailingEventPublisher(EventPublisher):
    async def publish(self, event) -> None:
        raise RuntimeError("simulated publisher failure")


class _FailingRepository(FakeEvaluationRepository):
    async def save(self, evaluation, *, event_id=None, root_cause_id=None, business_impact_id=None):
        raise RuntimeError("simulated persistence failure")


def _orchestrator_factory(repository) -> EvaluationOrchestrator:
    return EvaluationOrchestrator(
        validation_engine=ValidationEngine(),
        quality_engine=QualityEngine(),
        explainability_engine=ExplainabilityEngine(),
        confidence_analyzer=ConfidenceAnalyzer(),
        evaluation_builder=EvaluationBuilder(),
        repository=repository,
    )


@pytest.fixture
def wired_consumer():
    """
    Wires the real Consumer -> LifecycleService -> Orchestrator chain
    behind FakeEvaluationRepository, and exposes the repository/publisher
    for assertions. Mirrors Step 2's `wired_repository` fixture in
    test_api_evaluations.py, extended for Step 3's lifecycle dependencies.
    """
    repository = FakeEvaluationRepository()
    publisher = _RecordingEventPublisher()
    lifecycle_service = EvaluationLifecycleService(
        session_factory=_FakeSession,
        repository_factory=lambda session: repository,
        orchestrator_factory=_orchestrator_factory,
        event_publisher=publisher,
    )
    consumer = BusinessImpactCompletedConsumer(lifecycle_service)
    app.dependency_overrides[get_business_impact_completed_consumer] = lambda: consumer
    app.dependency_overrides[get_evaluation_repository] = lambda: repository
    yield repository, publisher
    app.dependency_overrides.clear()


def _valid_payload(**overrides) -> dict:
    payload = {
        "event_id": str(uuid.uuid4()),
        "incident_id": "INC-LIFECYCLE-0001",
        "root_cause": "service_outage",
        "root_cause_confidence_score": 85,
        "root_cause_explanation": "service_outage identified with critical anomaly severity",
        "root_cause_evidence_count": 2,
        "root_cause_id": str(uuid.uuid4()),
        "business_impact_overall_score": 75,
        "business_impact_overall_severity": "high",
        "business_impact_business_priority": "high",
        "business_impact_confidence": 80,
        "business_impact_explanation": (
            "Overall business impact is high (score: 75, priority: high). "
            "Reasons: financial (critical): incident severity is critical."
        ),
        "assessment_id": str(uuid.uuid4()),
    }
    payload.update(overrides)
    return payload


@pytest.mark.anyio
async def test_happy_path_completes_persists_and_publishes(wired_consumer):
    repository, publisher = wired_consumer
    payload = _valid_payload()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/internal/events/business-impact-completed", json=payload)
        assert response.status_code == 202
        body = response.json()
        assert body["outcome"] == "completed"
        evaluation_id = body["evaluation_id"]
        assert evaluation_id is not None

        get_response = await client.get(f"/api/v1/evaluations/{evaluation_id}")

    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched["incident_id"] == payload["incident_id"]
    assert fetched["root_cause_id"] == payload["root_cause_id"]
    assert fetched["business_impact_id"] == payload["assessment_id"]
    assert len(publisher.published) == 1
    assert str(publisher.published[0].caused_by_event_id) == payload["event_id"]
    assert len(repository.by_id) == 1


@pytest.mark.anyio
async def test_duplicate_event_is_rejected_and_nothing_new_is_persisted(wired_consumer):
    repository, _ = wired_consumer
    payload = _valid_payload()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = await client.post("/internal/events/business-impact-completed", json=payload)
        second = await client.post("/internal/events/business-impact-completed", json=payload)

    assert first.json()["outcome"] == "completed"
    assert second.json()["outcome"] == "rejected"
    assert len(repository.by_id) == 1


@pytest.mark.anyio
async def test_validation_rejection_persists_nothing(wired_consumer):
    repository, publisher = wired_consumer
    payload = _valid_payload(root_cause_confidence_score=999)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/internal/events/business-impact-completed", json=payload)

    assert response.status_code == 202
    assert response.json()["outcome"] == "rejected"
    assert repository.by_id == {}
    assert publisher.published == []


@pytest.mark.anyio
async def test_malformed_payload_is_rejected(wired_consumer):
    payload = _valid_payload()
    del payload["incident_id"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/internal/events/business-impact-completed", json=payload)

    assert response.status_code == 202
    assert response.json()["outcome"] == "rejected"


@pytest.mark.anyio
async def test_persistence_failure_is_reported_as_failed_and_nothing_is_published():
    repository = _FailingRepository()
    publisher = _RecordingEventPublisher()
    lifecycle_service = EvaluationLifecycleService(
        session_factory=_FakeSession,
        repository_factory=lambda session: repository,
        orchestrator_factory=_orchestrator_factory,
        event_publisher=publisher,
    )
    consumer = BusinessImpactCompletedConsumer(lifecycle_service)
    app.dependency_overrides[get_business_impact_completed_consumer] = lambda: consumer
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/internal/events/business-impact-completed", json=_valid_payload())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["outcome"] == "failed"
    assert publisher.published == []


@pytest.mark.anyio
async def test_publisher_failure_still_completes_and_the_evaluation_is_retrievable():
    repository = FakeEvaluationRepository()
    lifecycle_service = EvaluationLifecycleService(
        session_factory=_FakeSession,
        repository_factory=lambda session: repository,
        orchestrator_factory=_orchestrator_factory,
        event_publisher=_FailingEventPublisher(),
    )
    consumer = BusinessImpactCompletedConsumer(lifecycle_service)
    app.dependency_overrides[get_business_impact_completed_consumer] = lambda: consumer
    app.dependency_overrides[get_evaluation_repository] = lambda: repository
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/internal/events/business-impact-completed", json=_valid_payload())
            assert response.json()["outcome"] == "completed"
            evaluation_id = response.json()["evaluation_id"]

            get_response = await client.get(f"/api/v1/evaluations/{evaluation_id}")
    finally:
        app.dependency_overrides.clear()

    assert get_response.status_code == 200
