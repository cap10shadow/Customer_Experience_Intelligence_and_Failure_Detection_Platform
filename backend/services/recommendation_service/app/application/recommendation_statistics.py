from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class RecommendationStatistics:
    """
    Aggregate statistics computed across persisted Recommendation records.

    An Application-layer read model, not a Domain aggregate -- it has no
    identity, is never persisted, and is recomputed fresh on every request
    from whatever Recommendations currently exist. The same precedent
    already established by `evaluation_service`'s `EvaluationStatistics`:
    "Do NOT add a statistics method to the repository... implement it in
    an Application-layer query/statistics service."
    """

    total_count: int
    category_counts: Dict[str, int] = field(default_factory=dict)
    priority_counts: Dict[str, int] = field(default_factory=dict)
    average_score: float = 0.0
