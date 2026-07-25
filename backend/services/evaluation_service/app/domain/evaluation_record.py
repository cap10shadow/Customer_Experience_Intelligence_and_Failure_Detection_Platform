import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from backend.services.evaluation_service.app.domain.evaluation import Evaluation


@dataclass(frozen=True)
class EvaluationRecord:
    """
    A persisted Evaluation: the immutable Phase 8 Step 1 `Evaluation`
    aggregate plus the identity and relational metadata that only exist
    once persistence has occurred.

    Operational Purpose:
    `Evaluation` is, by design, identity-less (see its own docstring:
    "No evaluation_id: identity assignment is a persistence-layer
    concern"). `EvaluationRepository`'s read operations must return
    something a caller can address by ID, list, and paginate over --
    `EvaluationRecord` is that Domain-owned envelope, introduced in Phase 8
    Step 2 without modifying a single field of the frozen Step 1
    `Evaluation` aggregate.

    Architectural Boundaries:
    - Lives in the Domain layer (not Infrastructure) specifically so the
      Domain-defined `EvaluationRepository` interface can be expressed
      entirely in Domain types -- Infrastructure's `EvaluationModel` (ORM)
      is mapped into this by `EvaluationModelMapper`, and the Domain layer
      never sees the ORM type.
    - `root_cause_id` and `business_impact_id` are always None as of Step 2:
      neither `CompletedIntelligence` nor `DomainEvaluationContext` (Step 1)
      carry these upstream identifiers yet -- there is no source data to
      populate them from until a future step's event consumer supplies real
      Root Cause / Business Impact record IDs. This is a documented,
      deliberate gap, not an oversight (see Step 2 delivery notes).
    - Immutable and append-only, matching `Evaluation` itself: there is no
      operation anywhere in this service that mutates a persisted
      Evaluation record.
    """

    evaluation_id: uuid.UUID
    evaluation: Evaluation
    root_cause_id: Optional[uuid.UUID]
    business_impact_id: Optional[uuid.UUID]
    created_at: datetime
