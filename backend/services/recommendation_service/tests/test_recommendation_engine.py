import inspect

from backend.services.recommendation_service.app.domain.recommendation import Recommendation
from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_engine import RecommendationEngine, default_rules
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.recommendation_rule import RecommendationRule
from backend.shared.constants.enums.anomaly import AnomalySeverity
from backend.shared.constants.enums.complaint import SentimentLabel
from backend.shared.constants.enums.root_cause import RootCause


def test_default_rules_returns_one_rule_per_category():
    rules = default_rules()
    assert len(rules) == len(RecommendationCategory)
    assert all(isinstance(rule, RecommendationRule) for rule in rules)


def test_zero_recommendations_when_nothing_meaningful_is_present(
    make_incident, make_business_impact_summary, make_root_cause, make_intelligence_context
):
    context = make_intelligence_context(
        incident=make_incident(severity=AnomalySeverity.NORMAL),
        business_impact=make_business_impact_summary(overall_severity="medium"),
        root_cause=make_root_cause(confidence_score=90),
    )

    result = RecommendationEngine(rules=default_rules()).generate(context)

    assert result == ()


def test_golden_path_produces_a_complete_deterministic_response(
    make_incident, make_business_impact_summary, make_root_cause, make_nlp_intelligence, make_anomaly_intelligence,
    make_intelligence_context,
):
    context = make_intelligence_context(
        incident=make_incident(severity=AnomalySeverity.CRITICAL),
        business_impact=make_business_impact_summary(
            business_score=95,
            overall_severity="critical",
            business_priority="critical",
            confidence=90,
            financial_impact="critical",
            customer_impact="critical",
            operational_impact="high",
            sla_impact="critical",
            reputation_impact="high",
        ),
        root_cause=make_root_cause(cause=RootCause.SERVICE_OUTAGE, confidence_score=95),
        nlp_intelligence=make_nlp_intelligence(sentiment_label=SentimentLabel.HIGHLY_NEGATIVE),
        anomaly_intelligence=make_anomaly_intelligence(sla_breach_count=5),
    )

    result = RecommendationEngine(rules=default_rules()).generate(context)

    assert len(result) > 1
    assert all(isinstance(recommendation, Recommendation) for recommendation in result)
    categories = [recommendation.category for recommendation in result]
    assert RecommendationCategory.ESCALATE in categories
    # MONITOR never appears alongside urgent categories in a high-severity scenario.
    assert RecommendationCategory.MONITOR not in categories
    # Deterministic total ordering: priority ranks are non-decreasing across the result.
    from backend.services.recommendation_service.app.domain.precedence import priority_rank

    ranks = [priority_rank(recommendation.priority) for recommendation in result]
    assert ranks == sorted(ranks)


def test_multiple_recommendations_scenario_produces_independent_recommendations(
    make_incident, make_business_impact_summary, make_anomaly_intelligence, make_intelligence_context
):
    context = make_intelligence_context(
        incident=make_incident(severity=AnomalySeverity.MEDIUM),
        business_impact=make_business_impact_summary(sla_impact="high", operational_impact="medium"),
        anomaly_intelligence=make_anomaly_intelligence(sla_breach_count=1),
    )

    result = RecommendationEngine(rules=default_rules()).generate(context)

    categories = {recommendation.category for recommendation in result}
    assert RecommendationCategory.SLA_PROTECTION in categories
    assert RecommendationCategory.OPERATIONAL_ACTION in categories


def test_conflicting_recommendations_are_resolved_end_to_end(
    make_incident, make_business_impact_summary, make_anomaly_intelligence, make_intelligence_context
):
    """Low overall severity (would trigger Monitor) alongside active SLA breaches (a conflicting, urgent signal)."""
    context = make_intelligence_context(
        incident=make_incident(severity=AnomalySeverity.LOW),
        business_impact=make_business_impact_summary(overall_severity="low"),
        anomaly_intelligence=make_anomaly_intelligence(sla_breach_count=1),
    )

    result = RecommendationEngine(rules=default_rules()).generate(context)

    categories = {recommendation.category for recommendation in result}
    assert RecommendationCategory.MONITOR not in categories
    assert RecommendationCategory.SLA_PROTECTION in categories


def test_duplicate_recommendations_across_engine_runs_are_consolidated(make_intelligence_context):
    class _AlwaysMonitorTwiceRule(RecommendationRule):
        def evaluate(self, context):
            from backend.services.recommendation_service.app.domain.evidence_source import EvidenceSource
            from backend.services.recommendation_service.app.domain.supporting_evidence import SupportingEvidence

            evidence = (SupportingEvidence(source=EvidenceSource.INCIDENT, description="stub", weight=5),)
            recommendation = Recommendation(
                incident_id=context.incident.incident_id,
                category=RecommendationCategory.MONITOR,
                action="Monitor.",
                priority=RecommendationPriority.LOW,
                score=25,
                rationale="stub rationale",
                priority_rationale="stub priority rationale",
                supporting_evidence=evidence,
            )
            return (recommendation, recommendation)

    engine = RecommendationEngine(rules=(_AlwaysMonitorTwiceRule(),))
    context = make_intelligence_context()

    result = engine.generate(context)

    assert len(result) == 1


def test_is_deterministic_across_repeated_calls(
    make_incident, make_business_impact_summary, make_root_cause, make_intelligence_context
):
    context = make_intelligence_context(
        incident=make_incident(severity=AnomalySeverity.HIGH),
        business_impact=make_business_impact_summary(overall_severity="high", customer_impact="high"),
        root_cause=make_root_cause(cause=RootCause.LOGISTICS_DELAY, confidence_score=80),
    )
    engine = RecommendationEngine(rules=default_rules())

    first = engine.generate(context)
    second = engine.generate(context)

    assert first == second


def test_never_mutates_its_input(make_incident, make_intelligence_context):
    incident = make_incident(regions=("us-east",))
    context = make_intelligence_context(incident=incident)
    engine = RecommendationEngine(rules=default_rules())

    engine.generate(context)

    assert context.incident.regions == ("us-east",)  # unchanged (frozen dataclass anyway)


def test_adding_a_new_rule_requires_no_engine_changes(make_intelligence_context):
    class _StubRule(RecommendationRule):
        def evaluate(self, context):
            from backend.services.recommendation_service.app.domain.evidence_source import EvidenceSource
            from backend.services.recommendation_service.app.domain.supporting_evidence import SupportingEvidence

            evidence = (SupportingEvidence(source=EvidenceSource.INCIDENT, description="stub", weight=0),)
            return (
                Recommendation(
                    incident_id=context.incident.incident_id,
                    category=RecommendationCategory.MONITOR,
                    action="Stub action.",
                    priority=RecommendationPriority.LOW,
                    score=25,
                    rationale="stub",
                    priority_rationale="stub",
                    supporting_evidence=evidence,
                ),
            )

    engine = RecommendationEngine(rules=(_StubRule(),))

    result = engine.generate(make_intelligence_context())

    assert len(result) == 1
    assert result[0].action == "Stub action."


def test_a_rule_never_receives_or_calls_another_rule():
    # RecommendationRule.evaluate's signature only accepts the single
    # IntelligenceContext snapshot -- there is no parameter through which
    # one rule could reach another.
    signature = inspect.signature(RecommendationRule.evaluate)
    assert list(signature.parameters.keys()) == ["self", "context"]


def test_rule_evaluation_order_matches_default_rules_order():
    """default_rules()'s own ordering is the engine's rule evaluation order -- the final precedence tiebreak."""
    rules = default_rules()
    from backend.services.recommendation_service.app.domain.rules.escalation_rule import EscalationRule
    from backend.services.recommendation_service.app.domain.rules.monitor_rule import MonitorRule

    assert isinstance(rules[0], EscalationRule)
    assert isinstance(rules[-1], MonitorRule)
