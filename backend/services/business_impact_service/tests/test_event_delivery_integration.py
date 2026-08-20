"""
Cross-service integration tests (Part 6): drives the exact payloads
`BusinessImpactEventPublisher` would send through the REAL, unmodified
recommendation_service and evaluation_service FastAPI apps (via
`httpx.ASGITransport`, no network), proving -- with real consumer code, not
mocks -- that:

  - the same `event_id` is honored identically by both consumers
  - a duplicate delivery of the same event is recognized and not
    reprocessed (idempotency), on both consumer sides independently
  - fan-out is genuinely independent: nothing here makes one consumer's
    outcome depend on the other's

This is the only place in the repository a test imports another service's
own `tests.fakes` module -- deliberately, since event delivery is
inherently a cross-service concern; both consumers' own repository Fakes
are reused as-is (no database) rather than duplicated here.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.services.business_impact_service.app.domain.business_priority import BusinessPriority
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.models.business_impact_assessment import (
    BusinessImpactAssessmentEntity,
)
from backend.services.business_impact_service.app.repositories.root_cause_read_repository import PersistedRootCause
from backend.services.business_impact_service.app.services.business_impact_event_publisher import (
    BusinessImpactCompletedEvent,
    build_evaluation_payload,
    build_recommendation_payload,
)
from backend.shared.constants.enums.anomaly import AnomalySeverity
from backend.shared.constants.enums.business_impact_assessment import BusinessImpactAssessmentStatus
from backend.shared.constants.enums.root_cause import RootCause

from backend.services.evaluation_service.app.application.evaluation_orchestrator import EvaluationOrchestrator
from backend.services.evaluation_service.app.application.lifecycle.evaluation_lifecycle_service import (
    EvaluationLifecycleService,
)
from backend.services.evaluation_service.app.domain.confidence_analyzer import ConfidenceAnalyzer
from backend.services.evaluation_service.app.domain.evaluation_builder import EvaluationBuilder
from backend.services.evaluation_service.app.domain.explainability_engine import ExplainabilityEngine
from backend.services.evaluation_service.app.domain.quality_engine import QualityEngine
from backend.services.evaluation_service.app.domain.validation_engine import ValidationEngine
from backend.services.evaluation_service.app.infrastructure.messaging.consumers.business_impact_completed_consumer import (
    BusinessImpactCompletedConsumer as EvaluationConsumer,
)
from backend.services.evaluation_service.app.main import app as evaluation_app
from backend.services.evaluation_service.app.presentation.dependencies import (
    get_business_impact_completed_consumer as get_evaluation_consumer,
    get_evaluation_repository,
)
from backend.services.evaluation_service.tests.fakes import FakeEvaluationRepository

from backend.services.recommendation_service.app.application.lifecycle.recommendation_lifecycle_service import (
    RecommendationLifecycleService,
)
from backend.services.recommendation_service.app.application.orchestration.recommendation_orchestrator import (
    RecommendationOrchestrator,
)
from backend.services.recommendation_service.app.domain.recommendation_engine import RecommendationEngine, default_rules
from backend.services.recommendation_service.app.infrastructure.messaging.consumers.business_impact_completed_consumer import (
    BusinessImpactCompletedConsumer as RecommendationConsumer,
)
from backend.services.recommendation_service.app.main import app as recommendation_app
from backend.services.recommendation_service.app.presentation.dependencies import (
    get_business_impact_completed_consumer as get_recommendation_consumer,
    get_recommendation_repository,
)
from backend.services.recommendation_service.tests.fakes import FakeRecommendationRepository
from backend.shared.config.settings import settings
from backend.shared.security.internal_auth import INTERNAL_SECRET_HEADER

# Phase 13 Batch 4 (AD-5): both internal event routes now require the
# internal-service credential.
_INTERNAL_AUTH_HEADERS = {INTERNAL_SECRET_HEADER: settings.INTERNAL_SERVICE_SECRET}


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


class _NoopPublisher:
    async def publish(self, event) -> None:
        pass


def _build_event() -> BusinessImpactCompletedEvent:
    incident_id = uuid.uuid4()
    assessment = BusinessImpactAssessmentEntity(
        assessment_id=uuid.uuid4(),
        incident_id=incident_id,
        dataset_id=uuid.uuid4(),
        dataset_version_id=uuid.uuid4(),
        root_cause_id=uuid.uuid4(),
        financial=ImpactLevel.CRITICAL,
        customer=ImpactLevel.CRITICAL,
        operational=ImpactLevel.CRITICAL,
        sla=ImpactLevel.NONE,
        reputation=ImpactLevel.NONE,
        overall_score=75,
        overall_severity=ImpactLevel.HIGH,
        business_priority=BusinessPriority.HIGH,
        confidence=60,
        estimated_affected_customers=500,
        explanation="Overall business impact is high (score: 75, priority: high).",
        status=BusinessImpactAssessmentStatus.ACTIVE,
    )
    root_cause = PersistedRootCause(
        id=uuid.uuid4(),
        incident_id=incident_id,
        cause=RootCause.SERVICE_OUTAGE,
        confidence_score=90,
        confidence_level="Very High",
        evidence=[{"source": "anomaly_detection", "description": "spike", "weight": 5}],
        explanation="service_outage identified with critical anomaly severity",
    )
    return BusinessImpactCompletedEvent(
        event_id=uuid.uuid4(),
        incident_id=incident_id,
        dataset_id=uuid.uuid4(),
        incident_severity=AnomalySeverity.CRITICAL,
        assessment=assessment,
        root_cause=root_cause,
    )


@pytest.fixture
def wired_recommendation_app():
    repository = FakeRecommendationRepository()
    lifecycle_service = RecommendationLifecycleService(
        session_factory=_FakeSession,
        repository_factory=lambda session: repository,
        orchestrator_factory=lambda repo: RecommendationOrchestrator(
            engine=RecommendationEngine(rules=default_rules()), repository=repo
        ),
        event_publisher=_NoopPublisher(),
    )
    consumer = RecommendationConsumer(lifecycle_service)
    recommendation_app.dependency_overrides[get_recommendation_consumer] = lambda: consumer
    recommendation_app.dependency_overrides[get_recommendation_repository] = lambda: repository
    yield repository
    recommendation_app.dependency_overrides.clear()


@pytest.fixture
def wired_evaluation_app():
    repository = FakeEvaluationRepository()
    lifecycle_service = EvaluationLifecycleService(
        session_factory=_FakeSession,
        repository_factory=lambda session: repository,
        orchestrator_factory=lambda repo: EvaluationOrchestrator(
            validation_engine=ValidationEngine(),
            quality_engine=QualityEngine(),
            explainability_engine=ExplainabilityEngine(),
            confidence_analyzer=ConfidenceAnalyzer(),
            evaluation_builder=EvaluationBuilder(),
            repository=repo,
        ),
        event_publisher=_NoopPublisher(),
    )
    consumer = EvaluationConsumer(lifecycle_service)
    evaluation_app.dependency_overrides[get_evaluation_consumer] = lambda: consumer
    evaluation_app.dependency_overrides[get_evaluation_repository] = lambda: repository
    yield repository
    evaluation_app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_recommendation_consumer_accepts_the_publishers_real_payload_and_rejects_a_duplicate(
    wired_recommendation_app,
):
    event = _build_event()
    payload = build_recommendation_payload(event)

    transport = ASGITransport(app=recommendation_app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        first = await client.post("/internal/events/business-impact-completed", json=payload)
        second = await client.post("/internal/events/business-impact-completed", json=payload)

    assert first.status_code == 202
    assert first.json()["outcome"] == "completed"
    first_generation_id = first.json()["generation_id"]
    assert first_generation_id is not None

    assert second.status_code == 202
    assert second.json()["outcome"] == "rejected"
    # Idempotency: the duplicate resolves to the SAME generation, not a new one.
    assert second.json()["generation_id"] == first_generation_id


@pytest.mark.anyio
async def test_evaluation_consumer_accepts_the_publishers_real_payload_and_rejects_a_duplicate(wired_evaluation_app):
    event = _build_event()
    payload = build_evaluation_payload(event)

    transport = ASGITransport(app=evaluation_app)
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS) as client:
        first = await client.post("/internal/events/business-impact-completed", json=payload)
        second = await client.post("/internal/events/business-impact-completed", json=payload)

    assert first.status_code == 202
    assert first.json()["outcome"] == "completed"
    first_evaluation_id = first.json()["evaluation_id"]
    assert first_evaluation_id is not None

    assert second.status_code == 202
    assert second.json()["outcome"] == "rejected"
    assert second.json()["evaluation_id"] == first_evaluation_id


@pytest.mark.anyio
async def test_the_same_event_id_is_accepted_independently_by_both_real_consumers(
    wired_recommendation_app, wired_evaluation_app
):
    """Proves the parallel-fan-out contract end to end: one event_id, two independent real consumers, neither aware of the other."""
    event = _build_event()
    recommendation_payload = build_recommendation_payload(event)
    evaluation_payload = build_evaluation_payload(event)
    assert recommendation_payload["event_id"] == evaluation_payload["event_id"]

    async with AsyncClient(
        transport=ASGITransport(app=recommendation_app), base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS
    ) as recommendation_client, AsyncClient(
        transport=ASGITransport(app=evaluation_app), base_url="http://testserver", headers=_INTERNAL_AUTH_HEADERS
    ) as evaluation_client:
        recommendation_response = await recommendation_client.post(
            "/internal/events/business-impact-completed", json=recommendation_payload
        )
        evaluation_response = await evaluation_client.post(
            "/internal/events/business-impact-completed", json=evaluation_payload
        )

    assert recommendation_response.status_code == 202
    assert recommendation_response.json()["outcome"] == "completed"
    assert evaluation_response.status_code == 202
    assert evaluation_response.json()["outcome"] == "completed"
