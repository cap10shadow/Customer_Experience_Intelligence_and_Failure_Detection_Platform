import uuid
from abc import ABC, abstractmethod
from typing import List, Optional

from backend.services.evaluation_service.app.domain.evaluation import Evaluation
from backend.services.evaluation_service.app.domain.evaluation_record import EvaluationRecord


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
    """

    @abstractmethod
    async def save(self, evaluation: Evaluation) -> EvaluationRecord:
        """Persists a new, immutable Evaluation and returns it with its assigned identity."""
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
