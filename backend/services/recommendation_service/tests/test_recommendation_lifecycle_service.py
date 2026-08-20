"""
Unit tests for RecommendationLifecycleService: the Phase 9 Step 3 execution
lifecycle -- eligibility, idempotency, generation_id creation, transaction
boundary, and publish-after-commit -- exercised entirely in-memory against
FakeRecommendationRepository, the real RecommendationOrchestrator/Engine,
and fake session/publisher test doubles. No database or HTTP layer
involved; those are covered by the infrastructure/presentation test suites.
"""

import uuid

import pytest

from backend.services.recommendation_service.app.application.dto.recommendation_execution_request import (
    RecommendationExecutionRequest,
)
from backend.services.recommendation_service.app.application.lifecycle.recommendation_execution_result import (
    ExecutionOutcome,
)
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
from backend.shared.constants.enums.anomaly import AnomalySeverity
from backend.services.recommendation_service.tests.fakes import FakeRecommendationRepository


@pytest.fixture
def anyio_backend():
    return "asyncio"


DATASET_ID = uuid.uuid4()
DATASET_VERSION_ID = uuid.uuid4()


class _FakeSession:
    """Async-context-manager test double standing in for a real AsyncSession -- tracks commit/rollback calls."""

    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class _RefusingSessionFactory:
    """Session factory that fails the test if ever called -- proves eligibility rejects before touching a session."""

    def __call__(self) -> _FakeSession:
        raise AssertionError("session_factory must not be called when the request is ineligible")


class _UnreachableSessionFactory:
    """Simulates the database itself being unreachable: raises when opening a session, before any transaction starts."""

    def __call__(self) -> _FakeSession:
        raise ConnectionError("simulated: database unreachable")


class _FailingRepository(FakeRecommendationRepository):
    """FakeRecommendationRepository whose save_many() always raises, simulating a persistence/domain failure."""

    async def save_many(self, recommendations, *, dataset_id, dataset_version_id, incident_id, generation_id, event_id=None):
        raise RuntimeError("simulated persistence failure")


class _RecordingEventPublisher(RecommendationEventPublisher):
    def __init__(self) -> None:
        self.published = []

    async def publish(self, event) -> None:
        self.published.append(event)


class _FailingEventPublisher(RecommendationEventPublisher):
    async def publish(self, event) -> None:
        raise RuntimeError("simulated publisher failure")


def _orchestrator_factory(repository):
    return RecommendationOrchestrator(engine=RecommendationEngine(rules=default_rules()), repository=repository)


def _counting_orchestrator_factory(repository, call_counter: list):
    call_counter.append(1)
    return _orchestrator_factory(repository)


def _make_request(make_incident, make_business_impact_summary, make_intelligence_context, **overrides) -> RecommendationExecutionRequest:
    event_id = overrides.pop("event_id", uuid.uuid4())
    context = make_intelligence_context(
        incident=make_incident(**{k: v for k, v in overrides.items() if k in ("incident_id", "severity")}),
        business_impact=make_business_impact_summary(
            **{k: v for k, v in overrides.items() if k not in ("incident_id", "severity")}
        ),
    )
    return RecommendationExecutionRequest(event_id=event_id, dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, intelligence_context=context)


@pytest.mark.anyio
async def test_successful_execution_persists_and_publishes(make_incident, make_business_impact_summary, make_intelligence_context):
    repository = FakeRecommendationRepository()
    publisher = _RecordingEventPublisher()
    service = RecommendationLifecycleService(
        session_factory=_FakeSession,
        repository_factory=lambda session: repository,
        orchestrator_factory=_orchestrator_factory,
        event_publisher=publisher,
    )
    request = _make_request(make_incident, make_business_impact_summary, make_intelligence_context, overall_severity="critical")

    result = await service.execute(request)

    assert result.outcome == ExecutionOutcome.COMPLETED
    assert result.generation_id is not None
    assert result.recommendation_count == len(await repository.list_by_generation(result.generation_id, limit=100, offset=0))
    assert result.recommendation_count > 0
    assert len(publisher.published) == 1
    event = publisher.published[0]
    assert event.generation_id == result.generation_id
    assert event.recommendation_count == result.recommendation_count
    assert event.highest_priority == "critical"
    assert len(event.recommendations) == result.recommendation_count


@pytest.mark.anyio
async def test_duplicate_event_is_rejected_without_invoking_the_orchestrator(
    make_incident, make_business_impact_summary, make_intelligence_context
):
    repository = FakeRecommendationRepository()
    call_counter: list = []
    service = RecommendationLifecycleService(
        session_factory=_FakeSession,
        repository_factory=lambda session: repository,
        orchestrator_factory=lambda repo: _counting_orchestrator_factory(repo, call_counter),
        event_publisher=_RecordingEventPublisher(),
    )
    event_id = uuid.uuid4()
    first_request = _make_request(
        make_incident, make_business_impact_summary, make_intelligence_context, event_id=event_id, overall_severity="critical"
    )
    first_result = await service.execute(first_request)
    assert first_result.outcome == ExecutionOutcome.COMPLETED
    assert len(call_counter) == 1

    duplicate_request = _make_request(
        make_incident, make_business_impact_summary, make_intelligence_context, event_id=event_id, overall_severity="critical"
    )
    duplicate_result = await service.execute(duplicate_request)

    assert duplicate_result.outcome == ExecutionOutcome.REJECTED
    assert duplicate_result.generation_id == first_result.generation_id
    assert "duplicate" in duplicate_result.reason.lower()
    assert len(call_counter) == 1


@pytest.mark.anyio
async def test_duplicate_event_does_not_publish(make_incident, make_business_impact_summary, make_intelligence_context):
    repository = FakeRecommendationRepository()
    publisher = _RecordingEventPublisher()
    service = RecommendationLifecycleService(
        session_factory=_FakeSession,
        repository_factory=lambda session: repository,
        orchestrator_factory=_orchestrator_factory,
        event_publisher=publisher,
    )
    event_id = uuid.uuid4()
    await service.execute(
        _make_request(make_incident, make_business_impact_summary, make_intelligence_context, event_id=event_id, overall_severity="critical")
    )
    assert len(publisher.published) == 1

    await service.execute(
        _make_request(make_incident, make_business_impact_summary, make_intelligence_context, event_id=event_id, overall_severity="critical")
    )

    assert len(publisher.published) == 1  # unchanged -- the duplicate never published a second event


@pytest.mark.anyio
async def test_missing_event_id_is_rejected_before_any_session_is_opened(make_incident, make_business_impact_summary, make_intelligence_context):
    service = RecommendationLifecycleService(
        session_factory=_RefusingSessionFactory(),
        repository_factory=lambda session: (_ for _ in ()).throw(AssertionError("must not be called")),
        orchestrator_factory=_orchestrator_factory,
        event_publisher=_RecordingEventPublisher(),
    )
    context = make_intelligence_context(incident=make_incident(), business_impact=make_business_impact_summary())
    request = RecommendationExecutionRequest(event_id=None, dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, intelligence_context=context)

    result = await service.execute(request)

    assert result.outcome == ExecutionOutcome.REJECTED
    assert "event_id" in result.reason.lower()


@pytest.mark.anyio
async def test_zero_recommendation_execution_is_still_completed_and_published(
    make_incident, make_business_impact_summary, make_root_cause, make_intelligence_context
):
    repository = FakeRecommendationRepository()
    publisher = _RecordingEventPublisher()
    service = RecommendationLifecycleService(
        session_factory=_FakeSession,
        repository_factory=lambda session: repository,
        orchestrator_factory=_orchestrator_factory,
        event_publisher=publisher,
    )
    context = make_intelligence_context(
        incident=make_incident(severity=AnomalySeverity.NORMAL),
        business_impact=make_business_impact_summary(overall_severity="medium"),
        root_cause=make_root_cause(confidence_score=90),
    )
    request = RecommendationExecutionRequest(event_id=uuid.uuid4(), dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, intelligence_context=context)

    result = await service.execute(request)

    assert result.outcome == ExecutionOutcome.COMPLETED
    assert result.recommendation_count == 0
    assert len(publisher.published) == 1
    assert publisher.published[0].recommendation_count == 0
    assert publisher.published[0].highest_priority is None
    assert publisher.published[0].recommendations == ()


@pytest.mark.anyio
async def test_orchestrator_failure_rolls_back_and_returns_failed(make_incident, make_business_impact_summary, make_intelligence_context):
    repository = _FailingRepository()
    session = _FakeSession()
    service = RecommendationLifecycleService(
        session_factory=lambda: session,
        repository_factory=lambda s: repository,
        orchestrator_factory=_orchestrator_factory,
        event_publisher=_RecordingEventPublisher(),
    )
    request = _make_request(make_incident, make_business_impact_summary, make_intelligence_context, overall_severity="critical")

    result = await service.execute(request)

    assert result.outcome == ExecutionOutcome.FAILED
    assert "simulated persistence failure" in result.reason
    assert session.rolled_back is True
    assert session.committed is False
    assert repository.by_id == {}


@pytest.mark.anyio
async def test_publisher_failure_does_not_change_the_completed_outcome(make_incident, make_business_impact_summary, make_intelligence_context, caplog):
    repository = FakeRecommendationRepository()
    service = RecommendationLifecycleService(
        session_factory=_FakeSession,
        repository_factory=lambda session: repository,
        orchestrator_factory=_orchestrator_factory,
        event_publisher=_FailingEventPublisher(),
    )
    request = _make_request(make_incident, make_business_impact_summary, make_intelligence_context, overall_severity="critical")

    with caplog.at_level("CRITICAL"):
        result = await service.execute(request)

    assert result.outcome == ExecutionOutcome.COMPLETED
    assert len(await repository.list_by_generation(result.generation_id, limit=100, offset=0)) == result.recommendation_count
    assert any("manual reconciliation" in message for message in caplog.messages)


@pytest.mark.anyio
async def test_unreachable_database_propagates_as_an_exception(make_incident, make_business_impact_summary, make_intelligence_context):
    """
    A failure to even open a session (the database itself unreachable) has
    no transaction to roll back and must propagate uncaught -- this is the
    signal a real broker integration retries on, distinct from the
    deterministic REJECTED/FAILED outcomes returned for everything that
    happens once a session was actually opened.
    """
    service = RecommendationLifecycleService(
        session_factory=_UnreachableSessionFactory(),
        repository_factory=lambda session: FakeRecommendationRepository(),
        orchestrator_factory=_orchestrator_factory,
        event_publisher=_RecordingEventPublisher(),
    )
    request = _make_request(make_incident, make_business_impact_summary, make_intelligence_context, overall_severity="critical")

    with pytest.raises(ConnectionError, match="simulated: database unreachable"):
        await service.execute(request)


@pytest.mark.anyio
async def test_publish_happens_only_after_commit(make_incident, make_business_impact_summary, make_intelligence_context):
    """Ordering proof, not just end-state: commit must be recorded before publish is ever invoked."""
    call_order: list = []

    class _OrderTrackingSession(_FakeSession):
        async def commit(self) -> None:
            call_order.append("commit")
            await super().commit()

    class _OrderTrackingPublisher(RecommendationEventPublisher):
        async def publish(self, event) -> None:
            call_order.append("publish")

    repository = FakeRecommendationRepository()
    service = RecommendationLifecycleService(
        session_factory=_OrderTrackingSession,
        repository_factory=lambda session: repository,
        orchestrator_factory=_orchestrator_factory,
        event_publisher=_OrderTrackingPublisher(),
    )
    request = _make_request(make_incident, make_business_impact_summary, make_intelligence_context, overall_severity="critical")

    await service.execute(request)

    assert call_order == ["commit", "publish"]


@pytest.mark.anyio
async def test_generation_id_is_created_by_the_lifecycle_service_not_by_the_repository(
    make_incident, make_business_impact_summary, make_intelligence_context
):
    """Repository/Engine never mint generation_id; the LifecycleService always creates a fresh one per execution."""
    repository = FakeRecommendationRepository()
    service = RecommendationLifecycleService(
        session_factory=_FakeSession,
        repository_factory=lambda session: repository,
        orchestrator_factory=_orchestrator_factory,
        event_publisher=_RecordingEventPublisher(),
    )

    first = await service.execute(
        _make_request(make_incident, make_business_impact_summary, make_intelligence_context, overall_severity="critical")
    )
    second = await service.execute(
        _make_request(make_incident, make_business_impact_summary, make_intelligence_context, overall_severity="critical")
    )

    assert first.generation_id != second.generation_id
