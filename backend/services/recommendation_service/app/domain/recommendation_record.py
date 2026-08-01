import uuid
from dataclasses import dataclass
from datetime import datetime

from backend.services.recommendation_service.app.domain.recommendation import Recommendation


@dataclass(frozen=True)
class RecommendationRecord:
    """
    A persisted Recommendation: the immutable Phase 9 Step 1 `Recommendation`
    aggregate plus the identity and grouping metadata that only exist once
    persistence has occurred.

    Operational Purpose:
    `Recommendation` is, by design, identity-less (Step 1's frozen scope
    intentionally contains no persistence identity -- "IDs belong to Step
    2"). `RecommendationRepository`'s read operations must return something
    a caller can address by ID, list, and paginate over -- `RecommendationRecord`
    is that Domain-owned envelope, introduced in Step 2 without modifying a
    single field of the frozen Step 1 `Recommendation` aggregate. The exact
    same role `EvaluationRecord` plays for the (structurally identical)
    identity-less `Evaluation` aggregate in `evaluation_service`.

    Architectural Boundaries:
    - Lives in the Domain layer (not Infrastructure) specifically so the
      Domain-defined `RecommendationRepository` interface can be expressed
      entirely in Domain types -- Infrastructure's `RecommendationModel`
      (ORM) is mapped into this by `RecommendationModelMapper`, and the
      Domain layer never sees the ORM type.
    - `generation_id` is a bare identifier, not a `RecommendationGeneration`
      Domain Aggregate: per the frozen architecture, RecommendationGeneration
      is explicitly a persistence concept, not a Domain Aggregate, and the
      Domain Engine (`RecommendationEngine`, the Rules, the Consolidator)
      remains completely unaware of it. This record only carries the
      identifier value a caller needs to group/query by, the same way
      `EvaluationRecord.event_id` carries a bare event identifier without
      requiring an "Event" Domain Aggregate.
    - Immutable and append-only, matching `Recommendation` itself: there is
      no operation anywhere in this service that mutates a persisted
      Recommendation record.
    """

    recommendation_id: uuid.UUID
    recommendation: Recommendation
    generation_id: uuid.UUID
    created_at: datetime
