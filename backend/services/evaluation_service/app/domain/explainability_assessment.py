from dataclasses import dataclass
from typing import Tuple

from backend.services.evaluation_service.app.domain.evaluation_rating import EvaluationRating


@dataclass(frozen=True)
class ExplainabilityAssessment:
    """
    The ExplainabilityEngine's verdict: how well the upstream intelligence
    (Root Cause + Business Impact) explains itself for one Incident -- per
    ADR-006's evidence-chain principle, every stage should contribute
    evidence; this assessment is a deterministic check that it actually did.

    `findings` carries the deterministic reasons behind
    `explainability_score`, already decided by the engine -- never
    re-derived downstream.
    """
    explainability_score: int
    explainability_rating: EvaluationRating
    findings: Tuple[str, ...]
