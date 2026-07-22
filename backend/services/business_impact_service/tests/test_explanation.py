from backend.services.business_impact_service.app.domain.business_impact_profile import BusinessImpactProfile
from backend.services.business_impact_service.app.domain.business_priority import BusinessPriority
from backend.services.business_impact_service.app.domain.impact_dimension import ImpactDimension
from backend.services.business_impact_service.app.domain.impact_evaluation import ImpactEvaluation
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.services.explanation import build_explanation


def _profile() -> BusinessImpactProfile:
    return BusinessImpactProfile(
        financial=ImpactEvaluation(ImpactDimension.FINANCIAL, ImpactLevel.HIGH, "Critical-severity incident"),
        customer=ImpactEvaluation(ImpactDimension.CUSTOMER, ImpactLevel.MEDIUM, "120 customers affected"),
        operational=ImpactEvaluation(ImpactDimension.OPERATIONAL, ImpactLevel.NONE, "No operational signal"),
        sla=ImpactEvaluation(ImpactDimension.SLA, ImpactLevel.LOW, "1 SLA breach(es) recorded"),
        reputation=ImpactEvaluation(ImpactDimension.REPUTATION, ImpactLevel.NONE, "No negative sentiment signal detected"),
    )


def test_explanation_includes_overall_severity_score_and_priority():
    explanation = build_explanation(_profile(), business_score=62, overall_severity=ImpactLevel.MEDIUM, business_priority=BusinessPriority.MEDIUM)

    assert "medium" in explanation
    assert "score: 62" in explanation
    assert "priority: medium" in explanation


def test_explanation_aggregates_every_dimension_reason_verbatim():
    profile = _profile()
    explanation = build_explanation(profile, business_score=50, overall_severity=ImpactLevel.MEDIUM, business_priority=BusinessPriority.MEDIUM)

    for evaluation in profile.all_evaluations():
        assert evaluation.reason in explanation
        assert evaluation.impact_dimension.value in explanation


def test_explanation_never_invents_a_reason_not_present_in_the_profile():
    profile = _profile()
    explanation = build_explanation(profile, business_score=50, overall_severity=ImpactLevel.MEDIUM, business_priority=BusinessPriority.MEDIUM)

    reason_count = sum(explanation.count(evaluation.reason) for evaluation in profile.all_evaluations())
    assert reason_count == 5
