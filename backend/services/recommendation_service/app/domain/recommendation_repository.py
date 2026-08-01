import uuid
from abc import ABC, abstractmethod
from typing import List, Optional, Sequence

from backend.services.recommendation_service.app.domain.recommendation import Recommendation
from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.recommendation_record import RecommendationRecord


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
    """

    @abstractmethod
    async def save_many(
        self,
        recommendations: Sequence[Recommendation],
        *,
        incident_id: str,
        generation_id: uuid.UUID,
    ) -> List[RecommendationRecord]:
        """
        Persists the `RecommendationGeneration` row for this engine
        execution and every `Recommendation` it produced (zero or more),
        returning each with its assigned identity.
        """
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
