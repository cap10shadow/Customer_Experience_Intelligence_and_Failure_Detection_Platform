from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.rules.sla_protection_rule import (
    SLA_CRITICAL_BREACH_THRESHOLD,
    SLAProtectionRule,
)


def test_does_not_fire_without_breaches_or_meaningful_impact(
    make_anomaly_intelligence, make_business_impact_summary, make_intelligence_context
):
    context = make_intelligence_context(
        anomaly_intelligence=make_anomaly_intelligence(sla_breach_count=0),
        business_impact=make_business_impact_summary(sla_impact="low"),
    )

    assert SLAProtectionRule().evaluate(context) == ()


def test_fires_on_a_single_active_breach(make_anomaly_intelligence, make_intelligence_context):
    context = make_intelligence_context(anomaly_intelligence=make_anomaly_intelligence(sla_breach_count=1))

    result = SLAProtectionRule().evaluate(context)

    assert len(result) == 1
    assert result[0].category == RecommendationCategory.SLA_PROTECTION
    assert result[0].priority == RecommendationPriority.HIGH


def test_fires_at_critical_priority_at_the_breach_threshold(make_anomaly_intelligence, make_intelligence_context):
    context = make_intelligence_context(
        anomaly_intelligence=make_anomaly_intelligence(sla_breach_count=SLA_CRITICAL_BREACH_THRESHOLD)
    )

    result = SLAProtectionRule().evaluate(context)[0]

    assert result.priority == RecommendationPriority.CRITICAL


def test_fires_at_high_priority_just_below_the_breach_threshold(make_anomaly_intelligence, make_intelligence_context):
    context = make_intelligence_context(
        anomaly_intelligence=make_anomaly_intelligence(sla_breach_count=SLA_CRITICAL_BREACH_THRESHOLD - 1)
    )

    result = SLAProtectionRule().evaluate(context)[0]

    assert result.priority == RecommendationPriority.HIGH


def test_fires_on_meaningful_sla_impact_without_active_breaches(make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(business_impact=make_business_impact_summary(sla_impact="high"))

    assert len(SLAProtectionRule().evaluate(context)) == 1


def test_fires_at_critical_priority_on_critical_sla_impact(make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(business_impact=make_business_impact_summary(sla_impact="critical"))

    result = SLAProtectionRule().evaluate(context)[0]

    assert result.priority == RecommendationPriority.CRITICAL


def test_absent_anomaly_intelligence_does_not_prevent_evaluation(make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(
        anomaly_intelligence=None, business_impact=make_business_impact_summary(sla_impact="high")
    )

    assert len(SLAProtectionRule().evaluate(context)) == 1


def test_is_deterministic(make_anomaly_intelligence, make_intelligence_context):
    context = make_intelligence_context(anomaly_intelligence=make_anomaly_intelligence(sla_breach_count=2))

    assert SLAProtectionRule().evaluate(context) == SLAProtectionRule().evaluate(context)
