import uuid
from abc import ABC, abstractmethod
from typing import List, Optional

from backend.services.evaluation_service.app.domain.evaluation import Evaluation
from backend.services.evaluation_service.app.domain.evaluation_record import EvaluationRecord


class DuplicateEventError(Exception):
    """
    Raised by `EvaluationRepository.save()` when the supplied `event_id` has
    already been persisted for a prior Evaluation.

    Part of the Repository port's contract, not a "lifecycle" concept: it
    expresses a Repository-level invariant (one Evaluation per inbound
    event identifier, enforced by a database UNIQUE constraint as the
    correctness guarantee) the same way any repository documents the
    exceptions its own uniqueness rules can raise. Callers -- Application's
    `EvaluationLifecycleService` -- catch this to distinguish "this event
    was already processed" (a normal, expected outcome under concurrent
    duplicate delivery) from a genuine persistence failure.
    """


class EvaluationRepository(ABC):
    """
    Evaluation Repository (Domain-owned port)

    Operational Purpose:
    Defines the persistence contract the Evaluation Service depends on,
    without depending on any persistence technology itself. Infrastructure
    implements this interface (`PostgreSQLEvaluationRepository`); the
    Domain and Application layers depend only on this abstraction --
    Dependency Inversion, per Clean Architecture.

    Architectural Boundaries:
    - Expressed entirely in Domain types (`Evaluation`, `EvaluationRecord`)
      -- never an ORM model or any other Infrastructure type.
    - Evaluation records are immutable and append-only: there is no
      `update()` or `delete()` method here, and there never should be.
      Every new Evaluation is a new record; history is preserved through
      `evaluation_version` and `previous_evaluation_id`
      (`EvaluationRecord.evaluation.metadata`).
    - No `list_statistics()` here by design: aggregate statistics are an
      Application-layer concern (`EvaluationStatisticsService`), computed
      from the same read operations exposed here -- not a repository
      responsibility.
    - `get_by_event_id()` is the one Step 3 "lifecycle query" this port
      adds: `EvaluationLifecycleService`'s fast, application-level
      idempotency check reads through it before ever invoking the
      Orchestrator. It is a plain read, same shape as `get_by_id()` --
      it decides nothing and enforces nothing itself.
    """

    @abstractmethod
    async def save(
        self,
        evaluation: Evaluation,
        *,
        event_id: Optional[uuid.UUID] = None,
        root_cause_id: Optional[uuid.UUID] = None,
        business_impact_id: Optional[uuid.UUID] = None,
    ) -> EvaluationRecord:
        """
        Persists a new, immutable Evaluation and returns it with its
        assigned identity.

        `event_id`, `root_cause_id`, and `business_impact_id` are optional,
        caller-supplied relational/lineage metadata -- never derived by the
        repository itself. Omitting `event_id` (its Step 2 default) persists
        an Evaluation with no inbound-event lineage, as every Evaluation
        did before Step 3 introduced event-driven execution. Supplying a
        duplicate `event_id` raises `DuplicateEventError`, backed by a
        database UNIQUE constraint -- the correctness guarantee beneath
        `EvaluationLifecycleService`'s own faster, application-level check.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, evaluation_id: uuid.UUID) -> Optional[EvaluationRecord]:
        """Retrieves a single Evaluation by its own id."""
        raise NotImplementedError

    @abstractmethod
    async def get_latest(self, incident_id: str) -> Optional[EvaluationRecord]:
        """Retrieves the most recent Evaluation for the given incident, if any exists."""
        raise NotImplementedError

    @abstractmethod
    async def list_by_incident(
        self, incident_id: Optional[str] = None, *, limit: int, offset: int
    ) -> List[EvaluationRecord]:
        """
        Lists Evaluations, most recent first, optionally filtered to one
        incident. `incident_id=None` lists across all incidents (backs the
        general `GET /evaluations` collection endpoint).
        """
        raise NotImplementedError

    @abstractmethod
    async def list_history(self, incident_id: str, *, limit: int, offset: int) -> List[EvaluationRecord]:
        """Lists every Evaluation ever recorded for one incident, ordered by evaluation lineage (most recent first)."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_event_id(self, event_id: uuid.UUID) -> Optional[EvaluationRecord]:
        """Retrieves the Evaluation previously persisted for the given inbound event identifier, if any."""
        raise NotImplementedError
