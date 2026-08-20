import uuid
from typing import Optional, Tuple

from backend.services.recommendation_service.app.domain.intelligence_context import IntelligenceContext
from backend.services.recommendation_service.app.domain.recommendation_engine import RecommendationEngine
from backend.services.recommendation_service.app.domain.recommendation_record import RecommendationRecord
from backend.services.recommendation_service.app.domain.recommendation_repository import RecommendationRepository


class RecommendationOrchestrator:
    """
    Recommendation Orchestrator

    Layer:
    Application.

    Operational Purpose:
    Coordinates one Recommendation Engine execution: invokes the (frozen,
    unmodified) `RecommendationEngine` against an `IntelligenceContext`,
    receives the resulting immutable Recommendation collection, and
    persists it -- the `RecommendationGeneration` row and every
    Recommendation it produced -- through the injected
    `RecommendationRepository`. Returns the persisted result.

    Architectural Boundaries:
    - Orchestration and persistence coordination only: this class contains
      no lifecycle validation, no idempotency logic, and no messaging --
      it assumes execution has already been approved by
      `RecommendationLifecycleService` before it is ever invoked.
    - Never creates `generation_id`: per the frozen architecture, Generation
      identity belongs to the execution lifecycle
      (`RecommendationLifecycleService`), never to this orchestrator, the
      Repository, or the Engine. `generation_id` (and, when present,
      `event_id`) are supplied by the caller and forwarded verbatim to
      `RecommendationRepository.save_many()`.
    - Never publishes events: publishing is `RecommendationLifecycleService`'s
      responsibility, exercised only after this orchestrator's persistence
      has been committed.
    - Depends on `RecommendationEngine` and `RecommendationRepository` --
      the Engine is the exact, unmodified Step 1 component; the Repository
      is the Domain-defined port (Dependency Inversion), never a concrete
      implementation constructed here.
    - `DuplicateGenerationEventError` (raised by the Repository when a
      concurrent duplicate `event_id` is caught by the database's own
      UNIQUE constraint) is deliberately not caught here -- it propagates
      to `RecommendationLifecycleService`, the only component permitted to
      classify execution outcomes.
    """

    def __init__(self, engine: RecommendationEngine, repository: RecommendationRepository) -> None:
        self._engine = engine
        self._repository = repository

    async def execute(
        self,
        context: IntelligenceContext,
        *,
        generation_id: uuid.UUID,
        dataset_id: uuid.UUID,
        dataset_version_id: uuid.UUID,
        event_id: Optional[uuid.UUID] = None,
    ) -> Tuple[RecommendationRecord, ...]:
        """
        Runs the Recommendation Engine against `context` and persists every
        Recommendation it produced (zero or more) under the given
        `generation_id`. Returns the persisted, identity-bearing result.

        `dataset_id`/`dataset_version_id` (docs/DECISIONS.md AD-12) are
        forwarded verbatim to the Repository -- execution metadata supplied
        by the triggering event, not part of `IntelligenceContext`, so the
        (frozen) Recommendation Engine never sees or needs either.
        """
        recommendations = self._engine.generate(context)
        records = await self._repository.save_many(
            recommendations,
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
            incident_id=context.incident.incident_id,
            generation_id=generation_id,
            event_id=event_id,
        )
        return tuple(records)
