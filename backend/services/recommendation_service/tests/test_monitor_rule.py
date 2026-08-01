from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.rules.monitor_rule import MonitorRule


def test_does_not_fire_on_medium_severity(make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(business_impact=make_business_impact_summary(overall_severity="medium"))

    assert MonitorRule().evaluate(context) == ()


def test_does_not_fire_on_high_or_critical_severity(make_business_impact_summary, make_intelligence_context):
    for severity in ("high", "critical"):
        context = make_intelligence_context(business_impact=make_business_impact_summary(overall_severity=severity))
        assert MonitorRule().evaluate(context) == ()


def test_fires_on_low_severity(make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(business_impact=make_business_impact_summary(overall_severity="low"))

    result = MonitorRule().evaluate(context)

    assert len(result) == 1
    assert result[0].category == RecommendationCategory.MONITOR
    assert result[0].priority == RecommendationPriority.LOW


def test_fires_on_none_severity(make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(business_impact=make_business_impact_summary(overall_severity="none"))

    assert len(MonitorRule().evaluate(context)) == 1


def test_is_deterministic(make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(business_impact=make_business_impact_summary(overall_severity="low"))

    assert MonitorRule().evaluate(context) == MonitorRule().evaluate(context)
