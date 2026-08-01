from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.rules.mitigation_rule import (
    MITIGATION_CONFIDENCE_THRESHOLD,
    MitigationRule,
)
from backend.shared.constants.enums.root_cause import RootCause


def test_does_not_fire_without_a_root_cause(make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(
        root_cause=None, business_impact=make_business_impact_summary(overall_severity="high")
    )

    assert MitigationRule().evaluate(context) == ()


def test_does_not_fire_below_confidence_threshold(make_root_cause, make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(
        root_cause=make_root_cause(confidence_score=MITIGATION_CONFIDENCE_THRESHOLD - 1),
        business_impact=make_business_impact_summary(overall_severity="high"),
    )

    assert MitigationRule().evaluate(context) == ()


def test_fires_at_confidence_threshold_boundary(make_root_cause, make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(
        root_cause=make_root_cause(confidence_score=MITIGATION_CONFIDENCE_THRESHOLD),
        business_impact=make_business_impact_summary(overall_severity="high"),
    )

    result = MitigationRule().evaluate(context)

    assert len(result) == 1
    assert result[0].category == RecommendationCategory.MITIGATE


def test_does_not_fire_when_business_impact_is_not_meaningful(
    make_root_cause, make_business_impact_summary, make_intelligence_context
):
    context = make_intelligence_context(
        root_cause=make_root_cause(confidence_score=95),
        business_impact=make_business_impact_summary(overall_severity="medium"),
    )

    assert MitigationRule().evaluate(context) == ()


def test_priority_is_critical_when_overall_severity_is_critical(
    make_root_cause, make_business_impact_summary, make_intelligence_context
):
    context = make_intelligence_context(
        root_cause=make_root_cause(confidence_score=95, cause=RootCause.PAYMENT_GATEWAY_FAILURE),
        business_impact=make_business_impact_summary(overall_severity="critical"),
    )

    result = MitigationRule().evaluate(context)[0]

    assert result.priority == RecommendationPriority.CRITICAL
    assert "payment_gateway_failure" in result.action


def test_priority_is_high_when_overall_severity_is_high(make_root_cause, make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(
        root_cause=make_root_cause(confidence_score=95),
        business_impact=make_business_impact_summary(overall_severity="high"),
    )

    result = MitigationRule().evaluate(context)[0]

    assert result.priority == RecommendationPriority.HIGH


def test_is_deterministic(make_root_cause, make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(
        root_cause=make_root_cause(confidence_score=95), business_impact=make_business_impact_summary(overall_severity="high")
    )

    assert MitigationRule().evaluate(context) == MitigationRule().evaluate(context)
