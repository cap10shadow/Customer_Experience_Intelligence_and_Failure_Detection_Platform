from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.rules.customer_communication_rule import (
    CustomerCommunicationRule,
)
from backend.shared.constants.enums.complaint import SentimentLabel


def test_does_not_fire_on_neutral_sentiment_and_low_customer_impact(
    make_nlp_intelligence, make_business_impact_summary, make_intelligence_context
):
    context = make_intelligence_context(
        nlp_intelligence=make_nlp_intelligence(sentiment_label=SentimentLabel.NEUTRAL),
        business_impact=make_business_impact_summary(customer_impact="low"),
    )

    assert CustomerCommunicationRule().evaluate(context) == ()


def test_fires_on_negative_sentiment_alone(make_nlp_intelligence, make_intelligence_context):
    context = make_intelligence_context(nlp_intelligence=make_nlp_intelligence(sentiment_label=SentimentLabel.NEGATIVE))

    result = CustomerCommunicationRule().evaluate(context)

    assert len(result) == 1
    assert result[0].category == RecommendationCategory.CUSTOMER_COMMUNICATION
    assert result[0].priority == RecommendationPriority.MEDIUM


def test_fires_at_high_priority_on_highly_negative_sentiment(make_nlp_intelligence, make_intelligence_context):
    context = make_intelligence_context(
        nlp_intelligence=make_nlp_intelligence(sentiment_label=SentimentLabel.HIGHLY_NEGATIVE)
    )

    result = CustomerCommunicationRule().evaluate(context)[0]

    assert result.priority == RecommendationPriority.HIGH


def test_fires_on_meaningful_customer_impact_without_nlp_data(make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(business_impact=make_business_impact_summary(customer_impact="high"))

    result = CustomerCommunicationRule().evaluate(context)

    assert len(result) == 1
    assert result[0].priority == RecommendationPriority.MEDIUM


def test_fires_at_high_priority_on_critical_customer_impact(make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(business_impact=make_business_impact_summary(customer_impact="critical"))

    result = CustomerCommunicationRule().evaluate(context)[0]

    assert result.priority == RecommendationPriority.HIGH


def test_absent_nlp_intelligence_does_not_prevent_evaluation(make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(
        nlp_intelligence=None, business_impact=make_business_impact_summary(customer_impact="high")
    )

    assert len(CustomerCommunicationRule().evaluate(context)) == 1


def test_is_deterministic(make_nlp_intelligence, make_intelligence_context):
    context = make_intelligence_context(nlp_intelligence=make_nlp_intelligence(sentiment_label=SentimentLabel.NEGATIVE))

    assert CustomerCommunicationRule().evaluate(context) == CustomerCommunicationRule().evaluate(context)
