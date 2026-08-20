import logging
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.recommendation_service.app.application.dto.recommendation_execution_request import (
    RecommendationExecutionRequest,
)
from backend.services.recommendation_service.app.application.dto.recommendations_generated_event import (
    RecommendationSummaryPayload,
    RecommendationsGeneratedEvent,
)
from backend.services.recommendation_service.app.application.lifecycle.recommendation_execution_result import (
    ExecutionOutcome,
    RecommendationExecutionResult,
)
from backend.services.recommendation_service.app.application.orchestration.recommendation_orchestrator import (
    RecommendationOrchestrator,
)
from backend.services.recommendation_service.app.application.ports.recommendation_event_publisher import (
    RecommendationEventPublisher,
)
from backend.services.recommendation_service.app.domain.precedence import priority_rank
from backend.services.recommendation_service.app.domain.recommendation_record import RecommendationRecord
from backend.services.recommendation_service.app.domain.recommendation_repository import (
    DuplicateGenerationEventError,
    RecommendationRepository,
)

logger = logging.getLogger(__name__)

SHORT_RATIONALE_MAX_LENGTH = 120

SessionFactory = Callable[[], AsyncSession]
RepositoryFactory = Callable[[AsyncSession], RecommendationRepository]
OrchestratorFactory = Callable[[RecommendationRepository], RecommendationOrchestrator]


class RecommendationLifecycleService:
    """
    Recommendation Lifecycle Service

    Layer:
    Application.

    Operational Purpose:
    Coordinates the complete execution lifecycle for one inbound
    `BusinessImpactCompleted` event: validates execution eligibility,
    performs the fast application-level idempotency check, creates the
    `generation_id` for this execution, owns the transaction boundary
    across all of that, invokes `RecommendationOrchestrator`, and -- only
    after a successful commit -- publishes the `RecommendationsGenerated`
    completion event. Returns exactly one of the three terminal outcomes
    (COMPLETED, REJECTED, FAILED) to its caller (the Infrastructure Event
    Consumer). The execution unit this service coordinates is the
    `RecommendationGeneration` as a whole, never individual Recommendations.

    Architectural Boundaries:
    - Never computes a Recommendation itself and never persists directly --
      both belong to `RecommendationOrchestrator`/`RecommendationRepository`.
      This service only decides *whether* execution should proceed and
      *what* happened once it did.
    - Creates `generation_id` here, and only here: per the frozen
      architecture, "the Repository never creates generation identifiers"
      and "the Recommendation Engine never creates generation
      identifiers -- Generation identity belongs to the execution
      lifecycle." A fresh `uuid.uuid4()` is minted once eligibility and
      the fast idempotency check both pass, before invoking the
      Orchestrator.
    - Depends only on `RecommendationRepository` (via `repository_factory`)
      and `RecommendationEventPublisher` -- both Domain/Application-owned
      abstractions. `session_factory` is the one concrete,
      Infrastructure-shaped dependency this service takes, because owning
      the transaction boundary requires a real `AsyncSession` to commit or
      roll back -- the same shape `evaluation_service`'s
      `EvaluationLifecycleService` already established.
    - Transaction model: a fresh session is opened once per `execute()`
      call. Everything from the idempotency read through orchestration and
      persistence happens on that one session. `commit()` is called only
      once persistence has actually succeeded; `rollback()` is called for
      every failure path (validation rejection, duplicate-event race,
      domain/persistence exception) -- no partial RecommendationGeneration
      or partial Recommendation collection can ever be observed outside
      this method. A failure to even *open* the session (the database
      itself unreachable) is deliberately left unguarded here and
      propagates straight out of `execute()` -- there is no transaction to
      roll back if one was never started, and this is exactly the
      "retryable infrastructure exception" case the Infrastructure Event
      Consumer (and, beyond it, a real broker's retry policy) must see as
      a raised exception, not a returned outcome.
    - Publishing: `RecommendationsGenerated` is published only after
      `commit()` returns successfully, per the frozen pipeline, and
      exactly once per `RecommendationGeneration` -- never once per
      Recommendation, including when `recommendation_count == 0`. If
      `event_publisher.publish()` itself raises, that is logged at
      CRITICAL severity with enough operational detail for manual
      reconciliation and swallowed here -- the RecommendationGeneration is
      already durably persisted and committed; the Outbox Pattern is
      intentionally not implemented (accepted prototype-stage tradeoff),
      so this is the documented, deliberate gap, not an oversight. The
      outcome returned to the caller remains COMPLETED regardless of
      publish success.
    """

    def __init__(
        self,
        session_factory: SessionFactory,
        repository_factory: RepositoryFactory,
        orchestrator_factory: OrchestratorFactory,
        event_publisher: RecommendationEventPublisher,
    ) -> None:
        self._session_factory = session_factory
        self._repository_factory = repository_factory
        self._orchestrator_factory = orchestrator_factory
        self._event_publisher = event_publisher

    async def execute(self, request: RecommendationExecutionRequest) -> RecommendationExecutionResult:
        eligibility_rejection = self._check_eligibility(request)
        if eligibility_rejection is not None:
            return eligibility_rejection

        # Deliberately outside any try/except: a failure to open a session
        # at all (database unreachable) is a transient infrastructure
        # condition with no transaction to roll back, and must propagate.
        async with self._session_factory() as session:
            repository = self._repository_factory(session)

            existing_generation_id = await repository.get_generation_by_event_id(request.event_id)
            if existing_generation_id is not None:
                await session.rollback()
                return RecommendationExecutionResult(
                    outcome=ExecutionOutcome.REJECTED,
                    generation_id=existing_generation_id,
                    reason=f"Duplicate event: event_id={request.event_id} was already processed",
                )

            generation_id = uuid.uuid4()
            orchestrator = self._orchestrator_factory(repository)

            try:
                records = await orchestrator.execute(
                    request.intelligence_context,
                    generation_id=generation_id,
                    dataset_id=request.dataset_id,
                    dataset_version_id=request.dataset_version_id,
                    event_id=request.event_id,
                )
            except DuplicateGenerationEventError as exc:
                # The fast check above missed a concurrent duplicate;
                # the database UNIQUE constraint is the correctness
                # guarantee that actually caught it here.
                await session.rollback()
                return RecommendationExecutionResult(
                    outcome=ExecutionOutcome.REJECTED,
                    reason=f"Duplicate event (concurrent): {exc}",
                )
            except Exception as exc:  # noqa: BLE001 -- classified deliberately broadly; see docstring.
                await session.rollback()
                logger.error("Recommendation execution failed for event_id=%s: %s", request.event_id, exc)
                return RecommendationExecutionResult(outcome=ExecutionOutcome.FAILED, reason=str(exc))

            await session.commit()
            result = RecommendationExecutionResult(
                outcome=ExecutionOutcome.COMPLETED,
                generation_id=generation_id,
                recommendation_count=len(records),
            )

        await self._publish_completion(request, generation_id, records)
        return result

    def _check_eligibility(self, request: RecommendationExecutionRequest) -> Optional[RecommendationExecutionResult]:
        """
        Structural precondition gate, distinct from Domain's own
        Recommendation Engine (still run unchanged inside
        `RecommendationOrchestrator`): rejects requests too incomplete to
        even attempt execution against, before any database round trip.
        """
        if request.event_id is None:
            return RecommendationExecutionResult(outcome=ExecutionOutcome.REJECTED, reason="Missing event_id")
        if not request.intelligence_context.incident.incident_id:
            return RecommendationExecutionResult(outcome=ExecutionOutcome.REJECTED, reason="Missing incident_id")
        return None

    async def _publish_completion(
        self,
        request: RecommendationExecutionRequest,
        generation_id: uuid.UUID,
        records: Tuple[RecommendationRecord, ...],
    ) -> None:
        event = RecommendationsGeneratedEvent(
            generation_id=generation_id,
            incident_id=request.intelligence_context.incident.incident_id,
            recommendation_count=len(records),
            highest_priority=self._highest_priority(records),
            created_at=datetime.now(timezone.utc),
            recommendations=tuple(
                RecommendationSummaryPayload(
                    recommendation_id=record.recommendation_id,
                    category=record.recommendation.category.value,
                    priority=record.recommendation.priority.value,
                    action=record.recommendation.action,
                    short_rationale=self._shorten(record.recommendation.rationale),
                )
                for record in records
            ),
        )
        try:
            await self._event_publisher.publish(event)
        except Exception as exc:  # noqa: BLE001 -- must never re-raise; commit already succeeded.
            logger.critical(
                "Failed to publish RecommendationsGenerated for generation_id=%s (incident_id=%s, "
                "caused_by_event_id=%s) after a successful commit -- manual reconciliation required: %s",
                generation_id,
                request.intelligence_context.incident.incident_id,
                request.event_id,
                exc,
            )

    @staticmethod
    def _highest_priority(records: Tuple[RecommendationRecord, ...]) -> Optional[str]:
        if not records:
            return None
        most_urgent = min(records, key=lambda record: priority_rank(record.recommendation.priority))
        return most_urgent.recommendation.priority.value

    @staticmethod
    def _shorten(rationale: str) -> str:
        if len(rationale) <= SHORT_RATIONALE_MAX_LENGTH:
            return rationale
        return rationale[: SHORT_RATIONALE_MAX_LENGTH - 1].rstrip() + "…"
