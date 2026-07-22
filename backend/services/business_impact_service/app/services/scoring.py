# Centralised, deterministic scoring model for business impact -- every
# rule and the engine import point values / bands from here rather than
# hardcoding them, the same discipline used for root-cause evidence points
# (Phase 6 Step 1) and confidence bands (Phase 5/6).

from typing import Dict, List, Tuple

from backend.services.business_impact_service.app.domain.business_impact_profile import BusinessImpactProfile
from backend.services.business_impact_service.app.domain.business_priority import BusinessPriority
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel

# Deterministic points assigned to each ImpactLevel when computing the
# weighted business score. Evenly spaced -- no dimension's levels carry
# more resolution than another.
IMPACT_LEVEL_POINTS: Dict[ImpactLevel, int] = {
    ImpactLevel.NONE: 0,
    ImpactLevel.LOW: 25,
    ImpactLevel.MEDIUM: 50,
    ImpactLevel.HIGH: 75,
    ImpactLevel.CRITICAL: 100,
}

# Ordered weakest-to-strongest, used to step an ImpactLevel up by one band
# (e.g. when a rule's reinforcing signal escalates its verdict).
_LEVEL_ORDER: Tuple[ImpactLevel, ...] = (
    ImpactLevel.NONE,
    ImpactLevel.LOW,
    ImpactLevel.MEDIUM,
    ImpactLevel.HIGH,
    ImpactLevel.CRITICAL,
)

# (upper_bound_inclusive, severity) pairs, magnitude-based against the
# weighted business score -- the same fixed-band style as
# root_cause_service's confidence classification.
SEVERITY_BANDS: List[Tuple[int, ImpactLevel]] = [
    (20, ImpactLevel.NONE),
    (40, ImpactLevel.LOW),
    (60, ImpactLevel.MEDIUM),
    (80, ImpactLevel.HIGH),
]
# > 80 -> CRITICAL

# Overall severity maps 1:1 onto a business priority -- NONE/LOW severity
# is still worth routing at LOW priority (there is no "no priority" tier).
PRIORITY_BY_SEVERITY: Dict[ImpactLevel, BusinessPriority] = {
    ImpactLevel.NONE: BusinessPriority.LOW,
    ImpactLevel.LOW: BusinessPriority.LOW,
    ImpactLevel.MEDIUM: BusinessPriority.MEDIUM,
    ImpactLevel.HIGH: BusinessPriority.HIGH,
    ImpactLevel.CRITICAL: BusinessPriority.CRITICAL,
}


def escalate_level(level: ImpactLevel) -> ImpactLevel:
    """Steps `level` one band up, capped at CRITICAL."""
    index = _LEVEL_ORDER.index(level)
    return _LEVEL_ORDER[min(index + 1, len(_LEVEL_ORDER) - 1)]


def classify_severity(business_score: int) -> ImpactLevel:
    """Classifies a 0-100 weighted business score into its deterministic ImpactLevel band."""
    for upper_bound, level in SEVERITY_BANDS:
        if business_score <= upper_bound:
            return level
    return ImpactLevel.CRITICAL


def classify_business_priority(overall_severity: ImpactLevel) -> BusinessPriority:
    """Derives the deterministic BusinessPriority for an already-classified overall severity."""
    return PRIORITY_BY_SEVERITY[overall_severity]


def compute_confidence(profile: BusinessImpactProfile) -> int:
    """
    Deterministic confidence in this assessment: the proportion of the five
    impact dimensions that carried an actual signal (non-NONE) rather than
    a default, uninformative reading. NOT a probability or ML estimate --
    purely a measure of how complete the available intelligence was.
    """
    evaluations = profile.all_evaluations()
    informative = sum(1 for evaluation in evaluations if evaluation.impact_level != ImpactLevel.NONE)
    return round((informative / len(evaluations)) * 100)
