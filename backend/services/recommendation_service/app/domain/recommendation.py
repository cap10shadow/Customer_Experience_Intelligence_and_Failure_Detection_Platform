from dataclasses import dataclass
from typing import Tuple

from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.supporting_evidence import SupportingEvidence


@dataclass(frozen=True)
class Recommendation:
    """
    Recommendation Aggregate

    Operational Purpose:
    One actionable, deterministic operational recommendation linked to an
    Incident. The Recommendation Engine produces zero or more of these;
    together they represent the complete operational response to the
    Incident's current intelligence.

    Architectural Boundaries:
    - Immutable and framework-independent -- pure in-memory value object,
      no persistence identity (Step 1 scope; identity assignment belongs
      to Step 2, the same deferral Evaluation's own aggregate made for its
      Step 1).
    - Every field here is required and validated in `__post_init__`: a
      Recommendation without a category, priority, score, rationale,
      priority rationale, or supporting evidence is not a valid
      Recommendation at all -- "No Recommendation may exist without
      explainability" is enforced structurally, not left to callers.
    - `score` and `priority` are intentionally independent fields, per the
      frozen architecture -- neither is derived from the other here.
    """

    incident_id: str
    category: RecommendationCategory
    action: str
    priority: RecommendationPriority
    score: int
    rationale: str
    priority_rationale: str
    supporting_evidence: Tuple[SupportingEvidence, ...]

    def __post_init__(self) -> None:
        if not self.incident_id:
            raise ValueError("Recommendation requires an incident_id")
        if not self.action:
            raise ValueError("Recommendation requires a Recommended Action")
        if not 0 <= self.score <= 100:
            raise ValueError(f"Recommendation score must be within [0, 100], got {self.score}")
        if not self.rationale:
            raise ValueError("Recommendation requires a Recommendation Rationale")
        if not self.priority_rationale:
            raise ValueError("Recommendation requires a Priority Rationale")
        if not self.supporting_evidence:
            raise ValueError("Recommendation requires at least one piece of Supporting Evidence")
