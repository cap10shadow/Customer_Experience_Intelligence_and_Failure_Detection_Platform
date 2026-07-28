import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EvaluationCompletedEvent:
    """
    Evaluation Completed Event DTO (Application-owned)

    Operational Purpose:
    The outbound integration event `EvaluationLifecycleService` builds and
    hands to the injected `EventPublisher` once an Evaluation has been
    persisted and its transaction committed -- never before. This is the
    "what completed" payload; how it is transported (in-process today, a
    real broker later) is entirely an Infrastructure concern this DTO
    knows nothing about.

    Architectural Boundaries:
    - Built only from an already-persisted `EvaluationRecord` -- every
      field here is a verbatim copy, never recomputed or re-derived.
    - `event_id` here is a *new* identifier for this outbound event,
      distinct from the inbound `BusinessImpactCompleted` event's own
      `event_id` that triggered execution (carried separately as
      `caused_by_event_id`) -- outbound and inbound events are always
      distinct events, even though this one was caused by that one.
    """

    event_id: uuid.UUID
    caused_by_event_id: uuid.UUID
    evaluation_id: uuid.UUID
    incident_id: str
    quality_rating: str
    explainability_rating: str
    occurred_at: datetime
