import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Sequence

from backend.services.recommendation_service.app.domain.recommendation import Recommendation
from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_decision import RecommendationDecision
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.recommendation_record import RecommendationRecord


class DuplicateGenerationEventError(Exception):
    """
    Raised by `RecommendationRepository.save_many()` when the supplied
    `event_id` has already been persisted on a prior `RecommendationGeneration`.

    Part of the Repository port's contract, not "lifecycle" vocabulary --
    it expresses a Repository-level invariant (one RecommendationGeneration
    per inbound event identifier, enforced by a database UNIQUE constraint
    as the correctness guarantee), the exact same role
    `evaluation_service`'s `DuplicateEventError` plays for `Evaluation`.
    Callers -- Application's `RecommendationLifecycleService` -- catch this
    to distinguish "this event was already processed" (a normal, expected
    outcome under concurrent duplicate delivery) from a genuine persistence
    failure.
    """


class RecommendationRepository(ABC):
    """
    Recommendation Repository (Domain-owned port)

    Operational Purpose:
    Defines the persistence contract the Recommendation Service depends on,
    without depending on any persistence technology itself. Infrastructure
    implements this interface (`PostgreSQLRecommendationRepository`); the
    Domain and Application layers depend only on this abstraction --
    Dependency Inversion, per Clean Architecture, the same pattern already
    established by `evaluation_service`'s `EvaluationRepository`.

    Architectural Boundaries:
    - Expressed entirely in Domain types (`Recommendation`, `RecommendationRecord`,
      `RecommendationCategory`, `RecommendationPriority`) -- never an ORM
      model or any other Infrastructure type.
    - `save_many()` is this port's only write operation, matching Step 1's
      pipeline output shape (`RecommendationEngine.generate()` returns a
      whole collection, not one Recommendation at a time) and the frozen
      persistence model ("Persist one Recommendation per row" as a single
      batch belonging to one engine execution). `generation_id` is supplied
      by the caller, never generated here -- per the frozen architecture,
      Generation identifiers are created in Step 3; Step 2 only persists
      what it is given.
    - `incident_id` is a required, separate parameter on `save_many()`
      (not derived from the `recommendations` sequence) because that
      sequence may legitimately be empty -- Step 1's engine can produce
      zero Recommendations for a given `IntelligenceContext` -- and the
      `RecommendationGeneration` row (the audit record that "an engine
      execution happened for this incident") must still be persisted even
      then.
    - Recommendation records are immutable and append-only: there is no
      `update()` or `delete()` method here, and there never should be.
    - `get_latest_by_incident()` is this port's one Step 2 addition beyond
      the six repository methods the frozen scope names explicitly
      (`save_many`, `get_by_id`, `list_by_incident`, `list_by_generation`,
      `list_by_category`, `list_by_priority`) -- required to back the
      frozen `GET /incidents/{incident_id}/recommendations/latest`
      endpoint, and a pure "retrieve Recommendations" read, squarely
      within this port's stated responsibility.
    - No statistics method here by design, mirroring `EvaluationRepository`:
      aggregate statistics are an Application-layer concern
      (`RecommendationStatisticsService`), computed from the same read
      operations exposed here -- not a repository responsibility.
    - `event_id` (Step 3) is optional on `save_many()` -- omitting it (its
      Step 2 default) preserves every Step 2 caller's exact prior
      behavior. Supplying a duplicate `event_id` raises
      `DuplicateGenerationEventError`, backed by a database UNIQUE
      constraint on `recommendation_generations.event_id` -- the
      correctness guarantee beneath `RecommendationLifecycleService`'s
      own faster, application-level idempotency check.
    - `get_generation_by_event_id()` is this port's one Step 3 "lifecycle
      query" addition: `RecommendationLifecycleService`'s fast idempotency
      check reads through it before ever invoking the Orchestrator. It
      returns a bare `generation_id`, not a `RecommendationGeneration`
      Domain Aggregate -- per the frozen architecture,
      RecommendationGeneration is not a Domain Aggregate at all, so this
      port never introduces one just to answer "does a generation already
      exist for this event, and if so, which one."
    """

    @abstractmethod
    async def save_many(
        self,
        recommendations: Sequence[Recommendation],
        *,
        incident_id: str,
        generation_id: uuid.UUID,
        event_id: Optional[uuid.UUID] = None,
    ) -> List[RecommendationRecord]:
        """
        Persists the `RecommendationGeneration` row for this engine
        execution and every `Recommendation` it produced (zero or more),
        returning each with its assigned identity. Raises
        `DuplicateGenerationEventError` if `event_id` is supplied and
        already belongs to a previously persisted `RecommendationGeneration`.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_generation_by_event_id(self, event_id: uuid.UUID) -> Optional[uuid.UUID]:
        """Retrieves the `generation_id` previously persisted for the given inbound event identifier, if any."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, recommendation_id: uuid.UUID) -> Optional[RecommendationRecord]:
        """Retrieves a single Recommendation by its own id."""
        raise NotImplementedError

    @abstractmethod
    async def list_by_incident(
        self, incident_id: Optional[str] = None, *, limit: int, offset: int
    ) -> List[RecommendationRecord]:
        """
        Lists Recommendations, most recent first, optionally filtered to
        one incident. `incident_id=None` lists across all incidents (backs
        the general `GET /recommendations` collection endpoint).
        """
        raise NotImplementedError

    @abstractmethod
    async def list_by_generation(
        self, generation_id: uuid.UUID, *, limit: int, offset: int
    ) -> List[RecommendationRecord]:
        """Lists every Recommendation produced by one engine execution (one `RecommendationGeneration`)."""
        raise NotImplementedError

    @abstractmethod
    async def list_by_category(
        self, category: RecommendationCategory, *, limit: int, offset: int
    ) -> List[RecommendationRecord]:
        """Lists Recommendations, most recent first, filtered to one RecommendationCategory."""
        raise NotImplementedError

    @abstractmethod
    async def list_by_priority(
        self, priority: RecommendationPriority, *, limit: int, offset: int
    ) -> List[RecommendationRecord]:
        """Lists Recommendations, most recent first, filtered to one RecommendationPriority."""
        raise NotImplementedError

    @abstractmethod
    async def get_latest_by_incident(
        self, incident_id: str, *, limit: int, offset: int
    ) -> List[RecommendationRecord]:
        """Lists every Recommendation belonging to the most recent RecommendationGeneration for one incident."""
        raise NotImplementedError

    @abstractmethod
    async def update_decision(
        self,
        recommendation_id: uuid.UUID,
        *,
        decision: RecommendationDecision,
        note: Optional[str],
        decided_at: datetime,
        actor_id: Optional[uuid.UUID] = None,
    ) -> Optional[RecommendationRecord]:
        """
        Overwrites the decision state on one persisted Recommendation
        (Step 7.X G-01) -- the one deliberate exception to this port's
        otherwise fully immutable, append-only contract. Returns the
        updated record, or `None` if `recommendation_id` does not exist.

        Idempotent/repeated-decision behavior is deliberately simple:
        each call unconditionally overwrites `decision`/`decision_note`/
        `decided_at`/`decided_by`, matching G-01's original design --
        distinguishing "the same person changed their mind" from
        "someone else overwrote it" is exactly what the append-only
        `recommendation_decision_history` table (Phase 13 Batch 5, AD-3)
        exists to answer; the current-state row itself keeps its simple
        overwrite semantics.

        `actor_id` (Phase 13 Batch 5, AD-3) is the Gateway-attested
        principal, supplied by the caller -- never resolved here, and
        never derived from anything but the caller-provided value.
        `None` means "no known actor" (a pre-Phase-13-style call, or one
        made without a principal header), not an error. Every successful
        call -- `actor_id` present or not -- appends exactly one row to
        `recommendation_decision_history`, in the same unit of work as
        the current-state overwrite.
        """
        raise NotImplementedError
