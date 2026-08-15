import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from backend.services.recommendation_service.app.domain.recommendation import Recommendation
from backend.services.recommendation_service.app.domain.recommendation_decision import RecommendationDecision


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
    - `decision`/`decision_note`/`decided_at` (Step 7.X G-01) are the one
      deliberate exception to the row-level immutability described above:
      a persisted Recommendation's decision state can be overwritten via
      `RecommendationRepository.update_decision()`, while the
      `Recommendation` aggregate itself (and every other field on this
      record) remains exactly as append-only as before. All three default
      to `None`, meaning "no decision has ever been recorded" -- this
      Domain-owned envelope is where that distinction lives, not on the
      immutable `Recommendation` aggregate.
    - `decided_by` (Phase 13 Batch 5, AD-3) is the fourth field in that
      same exception: the Gateway-attested principal who made the
      current decision, populated only from `update_decision()`'s
      `actor_id` parameter -- never from client-supplied request data.
      Defaults to `None`, meaning either "no decision has ever been
      recorded" or "a decision was recorded with no known actor"
      (pre-Phase-13 rows, or a call made without a principal header).
    """

    recommendation_id: uuid.UUID
    recommendation: Recommendation
    generation_id: uuid.UUID
    created_at: datetime
    decision: Optional[RecommendationDecision] = None
    decision_note: Optional[str] = None
    decided_at: Optional[datetime] = None
    decided_by: Optional[uuid.UUID] = None
