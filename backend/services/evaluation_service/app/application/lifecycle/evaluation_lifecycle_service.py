import logging
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.evaluation_service.app.application.dto.evaluation_completed_event import (
    EvaluationCompletedEvent,
)
from backend.services.evaluation_service.app.application.dto.evaluation_execution_request import (
    EvaluationExecutionRequest,
)
from backend.services.evaluation_service.app.application.evaluation_orchestrator import EvaluationOrchestrator
from backend.services.evaluation_service.app.application.lifecycle.evaluation_execution_result import (
    EvaluationExecutionResult,
    ExecutionOutcome,
)
from backend.services.evaluation_service.app.application.ports.event_publisher import EventPublisher
from backend.services.evaluation_service.app.domain.evaluation_record import EvaluationRecord
from backend.services.evaluation_service.app.domain.evaluation_repository import (
    DuplicateEventError,
    EvaluationRepository,
)
from backend.services.evaluation_service.app.domain.validation_summary import ValidationSummary

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AsyncSession]
RepositoryFactory = Callable[[AsyncSession], EvaluationRepository]
OrchestratorFactory = Callable[[EvaluationRepository], EvaluationOrchestrator]


class EvaluationLifecycleService:
    """
    Evaluation Lifecycle Service

    Layer:
    Application.

    Operational Purpose:
    Coordinates the complete execution lifecycle for one inbound
    `BusinessImpactCompleted` event: validates execution eligibility,
    performs the fast application-level idempotency check, invokes
    `EvaluationOrchestrator` to run and persist the Evaluation, owns the
    transaction boundary across all of that, and -- only after a successful
    commit -- publishes the `EvaluationCompleted` completion event. Returns
    exactly one of the three terminal outcomes (COMPLETED, REJECTED,
    FAILED) to its caller (the Infrastructure Event Consumer).

    Architectural Boundaries:
    - Never computes an Evaluation itself and never persists directly --
      both belong to `EvaluationOrchestrator`/`EvaluationRepository`. This
      service only decides *whether* execution should proceed and *what*
      happened once it did.
    - Depends only on `EvaluationRepository` (via `repository_factory`) and
      `EventPublisher` -- both Domain/Application-owned abstractions.
      `session_factory` is the one concrete, Infrastructure-shaped
      dependency this service takes, because owning the transaction
      boundary (this service's one Step 3 responsibility no other
      component may take on) requires a real `AsyncSession` to commit or
      roll back. The *type* of repository built from that session
      (`PostgreSQLEvaluationRepository` today) is still supplied by the
      caller via `repository_factory`, never constructed here directly --
      Dependency Inversion is preserved at the repository/orchestrator
      boundary, exactly as it already was for the REST API in
      `presentation/dependencies.py`.
    - Transaction model: a fresh session is opened once per `execute()`
      call. Everything from the idempotency read through orchestration and
      persistence happens on that one session. `commit()` is called only
      once persistence has actually succeeded; `rollback()` is called for
      every failure path (validation rejection, duplicate-event race,
      domain/persistence exception) -- no partial Evaluation record can
      ever be observed outside this method. A failure to even *open* the
      session (the database itself unreachable) is deliberately left
      unguarded here and propagates straight out of `execute()` -- there is
      no transaction to roll back if one was never started, and this is
      exactly the "retryable infrastructure exception" case the
      Infrastructure Event Consumer (and, beyond it, a real broker's retry
      policy) must see as a raised exception, not a returned outcome.
    - Publishing: `EvaluationCompleted` is published only after `commit()`
      returns successfully, per the frozen pipeline. If `event_publisher.publish()`
      itself raises, that is logged at CRITICAL severity with enough
      operational detail for manual reconciliation and swallowed here --
      the Evaluation is already durably persisted and committed; the
      Outbox Pattern is intentionally not implemented (accepted
      prototype-stage tradeoff), so this is the documented, deliberate gap,
      not an oversight. The outcome returned to the caller remains
      COMPLETED regardless of publish success.
    """

    def __init__(
        self,
        session_factory: SessionFactory,
        repository_factory: RepositoryFactory,
        orchestrator_factory: OrchestratorFactory,
        event_publisher: EventPublisher,
    ) -> None:
        self._session_factory = session_factory
        self._repository_factory = repository_factory
        self._orchestrator_factory = orchestrator_factory
        self._event_publisher = event_publisher

    async def execute(self, request: EvaluationExecutionRequest) -> EvaluationExecutionResult:
        eligibility_rejection = self._check_eligibility(request)
        if eligibility_rejection is not None:
            return eligibility_rejection

        # Deliberately outside any try/except: a failure to open a session
        # at all (database unreachable) is a transient infrastructure
        # condition with no transaction to roll back, and must propagate.
        async with self._session_factory() as session:
            repository = self._repository_factory(session)

            existing = await repository.get_by_event_id(request.event_id)
            if existing is not None:
                await session.rollback()
                return EvaluationExecutionResult(
                    outcome=ExecutionOutcome.REJECTED,
                    evaluation_id=existing.evaluation_id,
                    reason=f"Duplicate event: event_id={request.event_id} was already processed",
                )

            orchestrator = self._orchestrator_factory(repository)

            try:
                execution_result = await orchestrator.evaluate(
                    request.completed_intelligence,
                    event_id=request.event_id,
                    root_cause_id=request.root_cause_id,
                    business_impact_id=request.assessment_id,
                )
            except DuplicateEventError as exc:
                # The fast check above missed a concurrent duplicate;
                # the database UNIQUE constraint is the correctness
                # guarantee that actually caught it here.
                await session.rollback()
                return EvaluationExecutionResult(
                    outcome=ExecutionOutcome.REJECTED,
                    reason=f"Duplicate event (concurrent): {exc}",
                )
            except Exception as exc:  # noqa: BLE001 -- classified deliberately broadly; see docstring.
                await session.rollback()
                logger.error("Evaluation execution failed for event_id=%s: %s", request.event_id, exc)
                return EvaluationExecutionResult(outcome=ExecutionOutcome.FAILED, reason=str(exc))

            if isinstance(execution_result, ValidationSummary):
                await session.rollback()
                return EvaluationExecutionResult(
                    outcome=ExecutionOutcome.REJECTED,
                    reason=f"Validation failed: {'; '.join(execution_result.reasons)}",
                )

            await session.commit()
            result = EvaluationExecutionResult(
                outcome=ExecutionOutcome.COMPLETED,
                evaluation_id=execution_result.evaluation_id,
            )

        await self._publish_completion(request, execution_result)
        return result

    def _check_eligibility(self, request: EvaluationExecutionRequest) -> Optional[EvaluationExecutionResult]:
        """
        Structural precondition gate, distinct from Domain's own business
        validation (`ValidationEngine`, still run unchanged inside
        `EvaluationOrchestrator`): rejects requests too incomplete to even
        attempt execution against, before any database round trip.
        """
        if request.event_id is None:
            return EvaluationExecutionResult(outcome=ExecutionOutcome.REJECTED, reason="Missing event_id")
        if not request.completed_intelligence.incident_id:
            return EvaluationExecutionResult(outcome=ExecutionOutcome.REJECTED, reason="Missing incident_id")
        return None

    async def _publish_completion(
        self, request: EvaluationExecutionRequest, evaluation_record: EvaluationRecord
    ) -> None:
        event = EvaluationCompletedEvent(
            event_id=uuid.uuid4(),
            caused_by_event_id=request.event_id,
            evaluation_id=evaluation_record.evaluation_id,
            incident_id=evaluation_record.evaluation.incident_id,
            quality_rating=evaluation_record.evaluation.quality_assessment.quality_rating.value,
            explainability_rating=evaluation_record.evaluation.explainability_assessment.explainability_rating.value,
            occurred_at=datetime.now(timezone.utc),
        )
        try:
            await self._event_publisher.publish(event)
        except Exception as exc:  # noqa: BLE001 -- must never re-raise; commit already succeeded.
            logger.critical(
                "Failed to publish EvaluationCompleted for evaluation_id=%s (incident_id=%s, "
                "caused_by_event_id=%s) after a successful commit -- manual reconciliation required: %s",
                evaluation_record.evaluation_id,
                evaluation_record.evaluation.incident_id,
                request.event_id,
                exc,
            )
