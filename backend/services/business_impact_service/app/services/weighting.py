# Centralised, deterministic dimension weights. Rules never see or apply
# a weight -- each rule only ever produces one dimension's ImpactLevel; the
# engine is solely responsible for combining dimensions, and it does so
# using these weights, never hardcoded per-rule.

from typing import Dict

from backend.services.business_impact_service.app.domain.business_impact_profile import BusinessImpactProfile
from backend.services.business_impact_service.app.domain.impact_dimension import ImpactDimension
from backend.services.business_impact_service.app.services.scoring import IMPACT_LEVEL_POINTS

DIMENSION_WEIGHTS: Dict[ImpactDimension, float] = {
    ImpactDimension.FINANCIAL: 0.35,
    ImpactDimension.CUSTOMER: 0.25,
    ImpactDimension.OPERATIONAL: 0.15,
    ImpactDimension.SLA: 0.15,
    ImpactDimension.REPUTATION: 0.10,
}

MAX_BUSINESS_SCORE = 100


def cap_score(raw_score: int) -> int:
    """Clamps a computed business score to the deterministic [0, MAX_BUSINESS_SCORE] range."""
    return max(0, min(raw_score, MAX_BUSINESS_SCORE))


def compute_business_score(profile: BusinessImpactProfile) -> int:
    """
    Computes the deterministic, weighted business score (0-100) from a
    complete BusinessImpactProfile: each dimension's ImpactLevel is
    converted to points and combined using the centralised dimension
    weights above.
    """
    weighted_total = sum(
        IMPACT_LEVEL_POINTS[evaluation.impact_level] * DIMENSION_WEIGHTS[evaluation.impact_dimension]
        for evaluation in profile.all_evaluations()
    )
    return cap_score(round(weighted_total))
