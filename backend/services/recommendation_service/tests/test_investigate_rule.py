from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.rules.investigate_rule import (
    INVESTIGATION_CONFIDENCE_THRESHOLD,
    InvestigateRule,
)


def test_fires_when_root_cause_is_absent(make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(root_cause=None, business_impact=make_business_impact_summary(overall_severity="low"))

    result = InvestigateRule().evaluate(context)

    assert len(result) == 1
    assert result[0].category == RecommendationCategory.INVESTIGATE


def test_fires_below_the_confidence_threshold(make_root_cause, make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(
        root_cause=make_root_cause(confidence_score=INVESTIGATION_CONFIDENCE_THRESHOLD - 1),
        business_impact=make_business_impact_summary(overall_severity="low"),
    )

    assert len(InvestigateRule().evaluate(context)) == 1


def test_does_not_fire_at_the_confidence_threshold_boundary(
    make_root_cause, make_business_impact_summary, make_intelligence_context
):
    context = make_intelligence_context(
        root_cause=make_root_cause(confidence_score=INVESTIGATION_CONFIDENCE_THRESHOLD),
        business_impact=make_business_impact_summary(overall_severity="low"),
    )

    assert InvestigateRule().evaluate(context) == ()


def test_priority_is_medium_when_business_impact_is_meaningful(
    make_business_impact_summary, make_intelligence_context
):
    context = make_intelligence_context(root_cause=None, business_impact=make_business_impact_summary(overall_severity="high"))

    result = InvestigateRule().evaluate(context)[0]

    assert result.priority == RecommendationPriority.MEDIUM


def test_priority_is_low_when_business_impact_is_not_meaningful(make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(root_cause=None, business_impact=make_business_impact_summary(overall_severity="low"))

    result = InvestigateRule().evaluate(context)[0]

    assert result.priority == RecommendationPriority.LOW


def test_is_deterministic(make_intelligence_context):
    context = make_intelligence_context(root_cause=None)

    assert InvestigateRule().evaluate(context) == InvestigateRule().evaluate(context)
