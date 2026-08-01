from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.rules.escalation_rule import EscalationRule
from backend.shared.constants.enums.anomaly import AnomalySeverity


def test_does_not_fire_when_nothing_is_critical(make_incident, make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(
        incident=make_incident(severity=AnomalySeverity.MEDIUM),
        business_impact=make_business_impact_summary(overall_severity="medium"),
    )

    assert EscalationRule().evaluate(context) == ()


def test_fires_on_critical_business_impact(make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(business_impact=make_business_impact_summary(overall_severity="critical"))

    result = EscalationRule().evaluate(context)

    assert len(result) == 1
    assert result[0].category == RecommendationCategory.ESCALATE
    assert result[0].priority == RecommendationPriority.CRITICAL


def test_fires_on_critical_incident_severity_alone(make_incident, make_intelligence_context):
    context = make_intelligence_context(incident=make_incident(severity=AnomalySeverity.CRITICAL))

    result = EscalationRule().evaluate(context)

    assert len(result) == 1
    assert result[0].category == RecommendationCategory.ESCALATE


def test_combined_signals_produce_more_evidence_and_a_higher_score(
    make_incident, make_business_impact_summary, make_intelligence_context
):
    only_business_impact = make_intelligence_context(
        business_impact=make_business_impact_summary(overall_severity="critical")
    )
    both_signals = make_intelligence_context(
        incident=make_incident(severity=AnomalySeverity.CRITICAL),
        business_impact=make_business_impact_summary(overall_severity="critical"),
    )

    single_signal_result = EscalationRule().evaluate(only_business_impact)[0]
    combined_result = EscalationRule().evaluate(both_signals)[0]

    assert len(combined_result.supporting_evidence) > len(single_signal_result.supporting_evidence)
    assert combined_result.score >= single_signal_result.score


def test_result_is_fully_explainable(make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(business_impact=make_business_impact_summary(overall_severity="critical"))

    recommendation = EscalationRule().evaluate(context)[0]

    assert recommendation.rationale
    assert recommendation.priority_rationale
    assert recommendation.supporting_evidence
    assert recommendation.incident_id == context.incident.incident_id


def test_is_deterministic(make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(business_impact=make_business_impact_summary(overall_severity="critical"))

    assert EscalationRule().evaluate(context) == EscalationRule().evaluate(context)
