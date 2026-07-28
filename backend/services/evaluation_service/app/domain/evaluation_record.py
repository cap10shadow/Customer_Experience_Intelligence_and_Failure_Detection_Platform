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
    - `root_cause_id` and `business_impact_id` were always None as of Step 2:
      neither `CompletedIntelligence` nor `DomainEvaluationContext` carried
      these upstream identifiers yet. Step 3's event consumer closes this
      gap -- a `BusinessImpactCompleted` event now supplies both real
      identifiers, which `EvaluationLifecycleService` threads through
      `EvaluationOrchestrator` to `EvaluationRepository.save()`. Evaluations
      persisted outside the event-driven lifecycle (or from before Step 3)
      still leave both fields `None`; this remains a valid, permanent state
      for this envelope, not a transitional one.
    - `event_id` is Step 3's addition: the inbound `BusinessImpactCompleted`
      event identifier that triggered this Evaluation's execution, `None`
      for any Evaluation persisted without going through the event-driven
      lifecycle. It is the field a database UNIQUE constraint is enforced
      on to guarantee at most one Evaluation per inbound event, independent
      of and stronger than any in-process idempotency check.
    - Immutable and append-only, matching `Evaluation` itself: there is no
      operation anywhere in this service that mutates a persisted
      Evaluation record.
    """

    evaluation_id: uuid.UUID
    evaluation: Evaluation
    root_cause_id: Optional[uuid.UUID]
    business_impact_id: Optional[uuid.UUID]
    created_at: datetime
    event_id: Optional[uuid.UUID] = None
