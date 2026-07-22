from backend.services.business_impact_service.app.domain.business_impact_profile import BusinessImpactProfile
from backend.services.business_impact_service.app.domain.business_priority import BusinessPriority
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel


def build_explanation(
    profile: BusinessImpactProfile,
    business_score: int,
    overall_severity: ImpactLevel,
    business_priority: BusinessPriority,
) -> str:
    """
    Formats a human-readable explanation for a completed BusinessImpactProfile.

    Pure formatting only -- every reason shown here was already decided by
    the ImpactRule that produced it; this function invents nothing and
    duplicates no rule logic.
    """
    reasons = "; ".join(
        f"{evaluation.impact_dimension.value} ({evaluation.impact_level.value}): {evaluation.reason}"
        for evaluation in profile.all_evaluations()
    )
    return (
        f"Overall business impact is {overall_severity.value} "
        f"(score: {business_score}, priority: {business_priority.value}). "
        f"Reasons: {reasons}."
    )
