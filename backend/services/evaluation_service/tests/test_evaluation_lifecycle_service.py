"""
Unit tests for EvaluationLifecycleService: the Phase 8 Step 3 execution
lifecycle -- eligibility, idempotency, orchestration, transaction
boundary, and publish-after-commit -- exercised entirely in-memory against
FakeEvaluationRepository, the real EvaluationOrchestrator and domain
engines, and fake session/publisher test doubles. No database or HTTP
layer involved; those are covered by the infrastructure/presentation test
suites.
"""

import uuid

import pytest

from backend.services.evaluation_service.app.application.dto.evaluation_execution_request import (
    EvaluationExecutionRequest,
)
from backend.services.evaluation_service.app.application.evaluation_orchestrator import EvaluationOrchestrator
from backend.services.evaluation_service.app.application.lifecycle.evaluation_execution_result import ExecutionOutcome
from backend.services.evaluation_service.app.application.lifecycle.evaluation_lifecycle_service import (
    EvaluationLifecycleService,
)
from backend.services.evaluation_service.app.application.ports.event_publisher import EventPublisher
from backend.services.evaluation_service.app.domain.confidence_analyzer import ConfidenceAnalyzer
from backend.services.evaluation_service.app.domain.evaluation_builder import EvaluationBuilder
from backend.services.evaluation_service.app.domain.explainability_engine import ExplainabilityEngine
from backend.services.evaluation_service.app.domain.quality_engine import QualityEngine
from backend.services.evaluation_service.app.domain.validation_engine import ValidationEngine
from backend.services.evaluation_service.tests.fakes import FakeEvaluationRepository


@pytest.fixture
def anyio_backend():
    return "asyncio"


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


class _FailingRepository(FakeEvaluationRepository):
    """FakeEvaluationRepository whose save() always raises, simulating a persistence/domain failure."""

    async def save(self, evaluation, *, event_id=None, root_cause_id=None, business_impact_id=None):
        raise RuntimeError("simulated persistence failure")


class _RecordingEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self.published = []

    async def publish(self, event) -> None:
        self.published.append(event)


class _FailingEventPublisher(EventPublisher):
    async def publish(self, event) -> None:
        raise RuntimeError("simulated publisher failure")


def _orchestrator_factory(repository):
    return EvaluationOrchestrator(
        validation_engine=ValidationEngine(),
        quality_engine=QualityEngine(),
        explainability_engine=ExplainabilityEngine(),
        confidence_analyzer=ConfidenceAnalyzer(),
        evaluation_builder=EvaluationBuilder(),
        repository=repository,
    )


def _counting_orchestrator_factory(repository, call_counter: list):
    call_counter.append(1)
    return _orchestrator_factory(repository)


def _make_request(make_completed_intelligence, **overrides) -> EvaluationExecutionRequest:
    return EvaluationExecutionRequest(
        event_id=overrides.pop("event_id", uuid.uuid4()),
        root_cause_id=overrides.pop("root_cause_id", uuid.uuid4()),
        assessment_id=overrides.pop("assessment_id", uuid.uuid4()),
        completed_intelligence=make_completed_intelligence(**overrides),
    )


@pytest.mark.anyio
async def test_successful_execution_persists_and_publishes(make_completed_intelligence):
    repository = FakeEvaluationRepository()
    publisher = _RecordingEventPublisher()
    service = EvaluationLifecycleService(
        session_factory=_FakeSession,
        repository_factory=lambda session: repository,
        orchestrator_factory=_orchestrator_factory,
        event_publisher=publisher,
    )
    request = _make_request(make_completed_intelligence)

    result = await service.execute(request)

    assert result.outcome == ExecutionOutcome.COMPLETED
    assert result.evaluation_id is not None
    stored = await repository.get_by_id(result.evaluation_id)
    assert stored is not None
    assert stored.event_id == request.event_id
    assert stored.root_cause_id == request.root_cause_id
    assert stored.business_impact_id == request.assessment_id
    assert len(publisher.published) == 1
    assert publisher.published[0].evaluation_id == result.evaluation_id
    assert publisher.published[0].caused_by_event_id == request.event_id


@pytest.mark.anyio
async def test_duplicate_event_is_rejected_without_invoking_the_orchestrator(make_completed_intelligence):
    repository = FakeEvaluationRepository()
    call_counter: list = []
    service = EvaluationLifecycleService(
        session_factory=_FakeSession,
        repository_factory=lambda session: repository,
        orchestrator_factory=lambda repo: _counting_orchestrator_factory(repo, call_counter),
        event_publisher=_RecordingEventPublisher(),
    )
    event_id = uuid.uuid4()
    first_request = _make_request(make_completed_intelligence, event_id=event_id)
    first_result = await service.execute(first_request)
    assert first_result.outcome == ExecutionOutcome.COMPLETED
    assert len(call_counter) == 1

    duplicate_request = _make_request(make_completed_intelligence, event_id=event_id)
    duplicate_result = await service.execute(duplicate_request)

    assert duplicate_result.outcome == ExecutionOutcome.REJECTED
    assert duplicate_result.evaluation_id == first_result.evaluation_id
    assert "duplicate" in duplicate_result.reason.lower()
    # The orchestrator factory is invoked once per attempted execution;
    # the duplicate must be rejected before a second attempt is made.
    assert len(call_counter) == 1
    assert len(repository.by_id) == 1


@pytest.mark.anyio
async def test_validation_rejection_persists_nothing(make_completed_intelligence):
    repository = FakeEvaluationRepository()
    service = EvaluationLifecycleService(
        session_factory=_FakeSession,
        repository_factory=lambda session: repository,
        orchestrator_factory=_orchestrator_factory,
        event_publisher=_RecordingEventPublisher(),
    )
    request = _make_request(make_completed_intelligence, incident_id="INC-VALID-0001", root_cause_confidence_score=999)

    result = await service.execute(request)

    assert result.outcome == ExecutionOutcome.REJECTED
    assert "validation failed" in result.reason.lower()
    assert repository.by_id == {}


@pytest.mark.anyio
async def test_missing_event_id_is_rejected_before_any_session_is_opened(make_completed_intelligence):
    service = EvaluationLifecycleService(
        session_factory=_RefusingSessionFactory(),
        repository_factory=lambda session: (_ for _ in ()).throw(AssertionError("must not be called")),
        orchestrator_factory=_orchestrator_factory,
        event_publisher=_RecordingEventPublisher(),
    )
    request = EvaluationExecutionRequest(
        event_id=None,
        root_cause_id=uuid.uuid4(),
        assessment_id=uuid.uuid4(),
        completed_intelligence=make_completed_intelligence(),
    )

    result = await service.execute(request)

    assert result.outcome == ExecutionOutcome.REJECTED
    assert "event_id" in result.reason.lower()


@pytest.mark.anyio
async def test_orchestrator_failure_rolls_back_and_returns_failed(make_completed_intelligence):
    repository = _FailingRepository()
    session = _FakeSession()
    service = EvaluationLifecycleService(
        session_factory=lambda: session,
        repository_factory=lambda s: repository,
        orchestrator_factory=_orchestrator_factory,
        event_publisher=_RecordingEventPublisher(),
    )
    request = _make_request(make_completed_intelligence)

    result = await service.execute(request)

    assert result.outcome == ExecutionOutcome.FAILED
    assert "simulated persistence failure" in result.reason
    assert session.rolled_back is True
    assert session.committed is False
    assert repository.by_id == {}


@pytest.mark.anyio
async def test_publisher_failure_does_not_change_the_completed_outcome(make_completed_intelligence, caplog):
    repository = FakeEvaluationRepository()
    service = EvaluationLifecycleService(
        session_factory=_FakeSession,
        repository_factory=lambda session: repository,
        orchestrator_factory=_orchestrator_factory,
        event_publisher=_FailingEventPublisher(),
    )
    request = _make_request(make_completed_intelligence)

    with caplog.at_level("CRITICAL"):
        result = await service.execute(request)

    assert result.outcome == ExecutionOutcome.COMPLETED
    assert await repository.get_by_id(result.evaluation_id) is not None
    assert any("manual reconciliation" in message for message in caplog.messages)


@pytest.mark.anyio
async def test_unreachable_database_propagates_as_an_exception(make_completed_intelligence):
    """
    A failure to even open a session (the database itself unreachable) has
    no transaction to roll back and must propagate uncaught -- this is the
    signal a real broker integration retries on, distinct from the
    deterministic REJECTED/FAILED outcomes returned for everything that
    happens once a session was actually opened.
    """
    service = EvaluationLifecycleService(
        session_factory=_UnreachableSessionFactory(),
        repository_factory=lambda session: FakeEvaluationRepository(),
        orchestrator_factory=_orchestrator_factory,
        event_publisher=_RecordingEventPublisher(),
    )
    request = _make_request(make_completed_intelligence)

    with pytest.raises(ConnectionError, match="simulated: database unreachable"):
        await service.execute(request)
