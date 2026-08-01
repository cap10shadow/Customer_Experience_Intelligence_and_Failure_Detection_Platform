from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.rules.infrastructure_action_rule import (
    InfrastructureActionRule,
)
from backend.shared.constants.enums.complaint import IssueCategory


def test_does_not_fire_without_matching_signal(make_incident, make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(
        incident=make_incident(categories=(IssueCategory.PAYMENT_ISSUE,)),
        business_impact=make_business_impact_summary(operational_impact="low"),
    )

    assert InfrastructureActionRule().evaluate(context) == ()


def test_fires_on_operational_failure_category(make_incident, make_intelligence_context):
    context = make_intelligence_context(incident=make_incident(categories=(IssueCategory.OPERATIONAL_FAILURE,)))

    result = InfrastructureActionRule().evaluate(context)

    assert len(result) == 1
    assert result[0].category == RecommendationCategory.INFRASTRUCTURE_ACTION


def test_fires_on_technical_issue_category(make_incident, make_intelligence_context):
    context = make_intelligence_context(incident=make_incident(categories=(IssueCategory.TECHNICAL_ISSUE,)))

    assert len(InfrastructureActionRule().evaluate(context)) == 1


def test_fires_on_meaningful_operational_impact_without_category_signal(make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(business_impact=make_business_impact_summary(operational_impact="high"))

    result = InfrastructureActionRule().evaluate(context)

    assert len(result) == 1
    assert result[0].priority == RecommendationPriority.MEDIUM


def test_fires_at_high_priority_on_critical_operational_impact(make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(business_impact=make_business_impact_summary(operational_impact="critical"))

    result = InfrastructureActionRule().evaluate(context)[0]

    assert result.priority == RecommendationPriority.HIGH


def test_is_deterministic(make_incident, make_intelligence_context):
    context = make_intelligence_context(incident=make_incident(categories=(IssueCategory.TECHNICAL_ISSUE,)))

    assert InfrastructureActionRule().evaluate(context) == InfrastructureActionRule().evaluate(context)
