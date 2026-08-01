"""
Integration tests for the Phase 9 Step 3 execution lifecycle, exercised
over real HTTP against the actual FastAPI app: BusinessImpactCompleted ->
Event Consumer -> RecommendationLifecycleService -> RecommendationOrchestrator
-> Recommendation Engine -> Repository -> RecommendationsGenerated.

Uses FakeRecommendationRepository (in-memory) wired behind the real
BusinessImpactCompletedConsumer/RecommendationLifecycleService/RecommendationOrchestrator,
via `app.dependency_overrides` -- the same pattern Step 2's own API tests
use for `get_recommendation_repository`. Genuine concurrent-duplicate
protection (the database UNIQUE constraint racing two real transactions)
is covered separately, against real PostgreSQL, in
test_postgresql_recommendation_repository.py -- an in-memory Fake has no
real transaction isolation to prove that guarantee with.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.services.recommendation_service.app.application.lifecycle.recommendation_lifecycle_service import (
    RecommendationLifecycleService,
)
from backend.services.recommendation_service.app.application.orchestration.recommendation_orchestrator import (
    RecommendationOrchestrator,
)
from backend.services.recommendation_service.app.application.ports.recommendation_event_publisher import (
    RecommendationEventPublisher,
)
from backend.services.recommendation_service.app.domain.recommendation_engine import RecommendationEngine, default_rules
from backend.services.recommendation_service.app.infrastructure.messaging.consumers.business_impact_completed_consumer import (
    BusinessImpactCompletedConsumer,
)
from backend.services.recommendation_service.app.main import app
from backend.services.recommendation_service.app.presentation.dependencies import (
    get_business_impact_completed_consumer,
    get_recommendation_repository,
)
from backend.services.recommendation_service.tests.fakes import FakeRecommendationRepository


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


class _RecordingEventPublisher(RecommendationEventPublisher):
    def __init__(self) -> None:
        self.published = []

    async def publish(self, event) -> None:
        self.published.append(event)


class _FailingEventPublisher(RecommendationEventPublisher):
    async def publish(self, event) -> None:
        raise RuntimeError("simulated publisher failure")


class _FailingRepository(FakeRecommendationRepository):
    async def save_many(self, recommendations, *, incident_id, generation_id, event_id=None):
        raise RuntimeError("simulated persistence failure")


def _orchestrator_factory(repository) -> RecommendationOrchestrator:
    return RecommendationOrchestrator(engine=RecommendationEngine(rules=default_rules()), repository=repository)


@pytest.fixture
def wired_consumer():
    """
    Wires the real Consumer -> LifecycleService -> Orchestrator chain
    behind FakeRecommendationRepository, and exposes the
    repository/publisher for assertions.
    """
    repository = FakeRecommendationRepository()
    publisher = _RecordingEventPublisher()
    lifecycle_service = RecommendationLifecycleService(
        session_factory=_FakeSession,
        repository_factory=lambda session: repository,
        orchestrator_factory=_orchestrator_factory,
        event_publisher=publisher,
    )
    consumer = BusinessImpactCompletedConsumer(lifecycle_service)
    app.dependency_overrides[get_business_impact_completed_consumer] = lambda: consumer
    app.dependency_overrides[get_recommendation_repository] = lambda: repository
    yield repository, publisher
    app.dependency_overrides.clear()


def _valid_payload(**overrides) -> dict:
    payload = {
        "event_id": str(uuid.uuid4()),
        "incident": {
            "incident_id": "INC-LIFECYCLE-0001",
            "severity": "critical",
            "categories": [],
            "regions": [],
            "urgency_levels": [],
        },
        "business_impact": {
            "business_score": 90,
            "overall_severity": "critical",
            "business_priority": "critical",
            "confidence": 80,
            "financial_impact": "critical",
            "customer_impact": "high",
            "operational_impact": "medium",
            "sla_impact": "high",
            "reputation_impact": "medium",
        },
        "root_cause": {"cause": "service_outage", "confidence_score": 85, "confidence_level": "High"},
        "nlp_intelligence": None,
        "anomaly_intelligence": None,
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
        generation_id = body["generation_id"]
        assert generation_id is not None
        assert body["recommendation_count"] > 0

        get_response = await client.get(f"/api/v1/recommendations/generations/{generation_id}")

    assert get_response.status_code == 200
    fetched = get_response.json()
    assert len(fetched) == body["recommendation_count"]
    assert all(item["incident_id"] == payload["incident"]["incident_id"] for item in fetched)
    assert len(publisher.published) == 1
    assert str(publisher.published[0].generation_id) == generation_id
    assert publisher.published[0].incident_id == payload["incident"]["incident_id"]
    assert publisher.published[0].highest_priority == "critical"
    assert len(publisher.published[0].recommendations) == body["recommendation_count"]
    assert len(repository.by_id) == body["recommendation_count"]


@pytest.mark.anyio
async def test_event_contract_excludes_heavy_payload(wired_consumer):
    _, publisher = wired_consumer
    payload = _valid_payload()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post("/internal/events/business-impact-completed", json=payload)

    summary = publisher.published[0].recommendations[0]
    assert hasattr(summary, "recommendation_id")
    assert hasattr(summary, "category")
    assert hasattr(summary, "priority")
    assert hasattr(summary, "action")
    assert hasattr(summary, "short_rationale")
    assert not hasattr(summary, "supporting_evidence")
    assert not hasattr(summary, "recommendation_rationale")
    assert not hasattr(summary, "priority_rationale")


@pytest.mark.anyio
async def test_duplicate_event_is_rejected_and_nothing_new_is_persisted(wired_consumer):
    repository, publisher = wired_consumer
    payload = _valid_payload()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = await client.post("/internal/events/business-impact-completed", json=payload)
        second = await client.post("/internal/events/business-impact-completed", json=payload)

    assert first.json()["outcome"] == "completed"
    assert second.json()["outcome"] == "rejected"
    assert second.json()["generation_id"] == first.json()["generation_id"]
    assert len(publisher.published) == 1  # no second event for the duplicate


@pytest.mark.anyio
async def test_malformed_payload_is_rejected(wired_consumer):
    payload = _valid_payload()
    del payload["incident"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/internal/events/business-impact-completed", json=payload)

    assert response.status_code == 202
    assert response.json()["outcome"] == "rejected"


@pytest.mark.anyio
async def test_zero_recommendation_execution_still_completes_and_publishes(wired_consumer):
    repository, publisher = wired_consumer
    payload = _valid_payload(
        incident={"incident_id": "INC-ZERO", "severity": "normal", "categories": [], "regions": [], "urgency_levels": []},
        business_impact={
            "business_score": 30,
            "overall_severity": "medium",
            "business_priority": "medium",
            "confidence": 40,
            "financial_impact": "low",
            "customer_impact": "low",
            "operational_impact": "low",
            "sla_impact": "low",
            "reputation_impact": "low",
        },
        root_cause={"cause": "unknown", "confidence_score": 90, "confidence_level": "High"},
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/internal/events/business-impact-completed", json=payload)

    assert response.status_code == 202
    body = response.json()
    assert body["outcome"] == "completed"
    assert body["recommendation_count"] == 0
    assert len(publisher.published) == 1
    assert publisher.published[0].recommendation_count == 0
    assert publisher.published[0].highest_priority is None


@pytest.mark.anyio
async def test_persistence_failure_is_reported_as_failed_and_nothing_is_published():
    repository = _FailingRepository()
    publisher = _RecordingEventPublisher()
    lifecycle_service = RecommendationLifecycleService(
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
    assert response.json()["generation_id"] is None
    assert publisher.published == []


@pytest.mark.anyio
async def test_publisher_failure_still_completes_and_the_generation_is_retrievable():
    repository = FakeRecommendationRepository()
    lifecycle_service = RecommendationLifecycleService(
        session_factory=_FakeSession,
        repository_factory=lambda session: repository,
        orchestrator_factory=_orchestrator_factory,
        event_publisher=_FailingEventPublisher(),
    )
    consumer = BusinessImpactCompletedConsumer(lifecycle_service)
    app.dependency_overrides[get_business_impact_completed_consumer] = lambda: consumer
    app.dependency_overrides[get_recommendation_repository] = lambda: repository
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/internal/events/business-impact-completed", json=_valid_payload())
            assert response.json()["outcome"] == "completed"
            generation_id = response.json()["generation_id"]

            get_response = await client.get(f"/api/v1/recommendations/generations/{generation_id}")
    finally:
        app.dependency_overrides.clear()

    assert get_response.status_code == 200
    assert len(get_response.json()) == response.json()["recommendation_count"]
