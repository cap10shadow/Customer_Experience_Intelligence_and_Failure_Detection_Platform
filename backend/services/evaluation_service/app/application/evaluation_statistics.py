from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class EvaluationStatistics:
    """
    Aggregate statistics computed across persisted Evaluation records.

    An Application-layer read model, not a Domain aggregate -- it has no
    identity, is never persisted, and is recomputed fresh on every request
    from whatever Evaluations currently exist (per the approved
    architecture: "Do NOT add list_statistics() to the repository...
    implement them in an Application-layer query/statistics service").
    """

    total_count: int
    quality_rating_counts: Dict[str, int] = field(default_factory=dict)
    explainability_rating_counts: Dict[str, int] = field(default_factory=dict)
    average_quality_score: float = 0.0
    average_explainability_score: float = 0.0
    average_confidence: float = 0.0
