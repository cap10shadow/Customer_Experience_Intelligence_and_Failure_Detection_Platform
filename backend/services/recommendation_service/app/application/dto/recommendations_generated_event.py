import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple


@dataclass(frozen=True)
class RecommendationSummaryPayload:
    """
    One Recommendation's lightweight representation inside a
    `RecommendationsGeneratedEvent`. Deliberately excludes
    `supporting_evidence`, the full `recommendation_rationale`, and the
    full `priority_rationale` -- consumers needing those retrieve them
    through the Recommendation APIs (`GET /recommendations/{recommendation_id}`),
    per the frozen Consumer Experience Principle.
    """

    recommendation_id: uuid.UUID
    category: str
    priority: str
    action: str
    short_rationale: str


@dataclass(frozen=True)
class RecommendationsGeneratedEvent:
    """
    RecommendationsGenerated Event DTO (Application-owned)

    Operational Purpose:
    The outbound integration event `RecommendationLifecycleService` builds
    and hands to the injected `RecommendationEventPublisher` once one
    `RecommendationGeneration` (and every Recommendation it produced) has
    been persisted and its transaction committed -- never before. Exactly
    one of these is published per `RecommendationGeneration`, never one
    per Recommendation.

    Architectural Boundaries:
    - Intentionally lightweight: carries generation metadata
      (`generation_id`, `incident_id`, `recommendation_count`,
      `highest_priority`, `created_at`) plus one `RecommendationSummaryPayload`
      per Recommendation -- never `supporting_evidence`, the full
      rationale fields, JSONB persistence payloads, or a complete
      `Recommendation`/`RecommendationRecord`. Consumers needing complete
      Recommendation information must retrieve it through the
      Recommendation APIs, per the frozen Consumer Experience Principle.
    - Built only from already-persisted `RecommendationRecord`s -- every
      field here is a verbatim copy (or a simple derived summary, e.g.
      `highest_priority`), never recomputed or re-derived business logic.
    - `highest_priority` is `None` only when `recommendation_count == 0`
      -- the zero-Recommendation-execution case the frozen architecture
      explicitly treats as a normal, successful outcome still worth
      publishing.
    """

    generation_id: uuid.UUID
    incident_id: str
    recommendation_count: int
    highest_priority: Optional[str]
    created_at: datetime
    recommendations: Tuple[RecommendationSummaryPayload, ...]
