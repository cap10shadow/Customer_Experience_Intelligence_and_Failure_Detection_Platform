from dataclasses import dataclass
from typing import Tuple

from backend.services.evaluation_service.app.domain.evaluation_rating import EvaluationRating


@dataclass(frozen=True)
class QualityAssessment:
    """
    The QualityEngine's verdict: how complete and substantive the upstream
    intelligence (Root Cause + Business Impact) is for one Incident.

    `findings` carries the deterministic reasons behind `quality_score`,
    already decided by the engine -- never re-derived downstream.
    """
    quality_score: int
    quality_rating: EvaluationRating
    findings: Tuple[str, ...]
