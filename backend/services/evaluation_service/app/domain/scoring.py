# Centralised, deterministic banding for the Evaluation Service's own
# engines. QualityEngine and ExplainabilityEngine each own their own point
# values (mirroring how each root_cause_service rule owns its own evidence
# points), but both classify their final 0-100 score into an EvaluationRating
# using this single, shared banding function -- the same discipline used by
# root_cause_service's confidence bands and business_impact_service's
# severity bands.

from typing import List, Tuple

from backend.services.evaluation_service.app.domain.evaluation_rating import EvaluationRating

MAX_SCORE = 100

RATING_BANDS: List[Tuple[int, EvaluationRating]] = [
    (40, EvaluationRating.LOW),
    (75, EvaluationRating.MEDIUM),
]
# > 75 -> HIGH


def cap_score(raw_score: int) -> int:
    """Clamps a raw summed score to the deterministic [0, MAX_SCORE] range."""
    return max(0, min(raw_score, MAX_SCORE))


def classify_rating(score: int) -> EvaluationRating:
    """Classifies a 0-100 score into its deterministic EvaluationRating band."""
    for upper_bound, rating in RATING_BANDS:
        if score <= upper_bound:
            return rating
    return EvaluationRating.HIGH
