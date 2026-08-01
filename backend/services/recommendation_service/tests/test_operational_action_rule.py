from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.rules.operational_action_rule import OperationalActionRule
from backend.shared.constants.enums.complaint import IssueCategory


def test_does_not_fire_without_matching_signal(make_incident, make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(
        incident=make_incident(categories=(IssueCategory.TECHNICAL_ISSUE,)),
        business_impact=make_business_impact_summary(operational_impact="low"),
    )

    assert OperationalActionRule().evaluate(context) == ()


def test_fires_on_account_issue_category(make_incident, make_intelligence_context):
    context = make_intelligence_context(incident=make_incident(categories=(IssueCategory.ACCOUNT_ISSUE,)))

    result = OperationalActionRule().evaluate(context)

    assert len(result) == 1
    assert result[0].category == RecommendationCategory.OPERATIONAL_ACTION
    assert result[0].priority == RecommendationPriority.MEDIUM


def test_fires_on_subscription_or_refund_categories(make_incident, make_intelligence_context):
    for category in (IssueCategory.SUBSCRIPTION_ISSUE, IssueCategory.REFUND_ISSUE):
        context = make_intelligence_context(incident=make_incident(categories=(category,)))
        assert len(OperationalActionRule().evaluate(context)) == 1


def test_fires_on_medium_operational_impact_alone(make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(business_impact=make_business_impact_summary(operational_impact="medium"))

    assert len(OperationalActionRule().evaluate(context)) == 1


def test_does_not_fire_on_high_operational_impact_alone(make_business_impact_summary, make_intelligence_context):
    """High/critical operational impact is InfrastructureActionRule's territory, not this rule's."""
    context = make_intelligence_context(business_impact=make_business_impact_summary(operational_impact="high"))

    assert OperationalActionRule().evaluate(context) == ()


def test_is_deterministic(make_incident, make_intelligence_context):
    context = make_intelligence_context(incident=make_incident(categories=(IssueCategory.ACCOUNT_ISSUE,)))

    assert OperationalActionRule().evaluate(context) == OperationalActionRule().evaluate(context)
