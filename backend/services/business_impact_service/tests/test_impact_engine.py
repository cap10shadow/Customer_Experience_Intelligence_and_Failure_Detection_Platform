import pytest

from backend.services.business_impact_service.app.domain.impact_dimension import ImpactDimension
from backend.services.business_impact_service.app.domain.impact_evaluation import ImpactEvaluation
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.domain.impact_rule import ImpactRule
from backend.services.business_impact_service.app.services.impact_engine import BusinessImpactEngine, default_rules
from backend.services.business_impact_service.app.services.rules.customer_rule import CustomerRule
from backend.services.business_impact_service.app.services.rules.financial_rule import FinancialRule
from backend.services.business_impact_service.app.services.rules.operational_rule import OperationalRule
from backend.services.business_impact_service.app.services.rules.reputation_rule import ReputationRule
from backend.services.business_impact_service.app.services.rules.sla_rule import SLARule
from backend.shared.constants.enums.anomaly import AnomalySeverity
from backend.shared.constants.enums.complaint import UrgencyLabel
from backend.shared.constants.enums.root_cause import RootCause


class _StubRule(ImpactRule):
    """A minimal, self-contained ImpactRule used to prove the engine needs
    no changes to accept a rule for a fixed dimension/level."""

    def __init__(self, dimension: ImpactDimension, level: ImpactLevel):
        self._dimension = dimension
        self._level = level

    def evaluate(self, incident, root_cause, trend_metrics, anomaly_metrics) -> ImpactEvaluation:
        return ImpactEvaluation(impact_dimension=self._dimension, impact_level=self._level, reason="stub")


def _stub_rules(levels):
    return [
        _StubRule(ImpactDimension.FINANCIAL, levels[0]),
        _StubRule(ImpactDimension.CUSTOMER, levels[1]),
        _StubRule(ImpactDimension.OPERATIONAL, levels[2]),
        _StubRule(ImpactDimension.SLA, levels[3]),
        _StubRule(ImpactDimension.REPUTATION, levels[4]),
    ]


def test_default_rules_returns_all_five_built_in_rules():
    rules = default_rules()
    assert len(rules) == 5
    assert {type(rule) for rule in rules} == {FinancialRule, CustomerRule, OperationalRule, SLARule, ReputationRule}


def test_engine_produces_a_complete_assessment_with_default_rules(
    make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics
):
    engine = BusinessImpactEngine(rules=default_rules())
    incident = make_incident(
        incident_id="INC-0042",
        severity=AnomalySeverity.CRITICAL,
        urgency_levels=(UrgencyLabel.CRITICAL,),
        regions=("us-east", "us-west"),
    )
    root_cause = make_root_cause(cause=RootCause.SERVICE_OUTAGE)
    trend = make_trend_metrics(percentage_change=60.0)
    anomaly = make_anomaly_metrics(
        severity=AnomalySeverity.CRITICAL,
        affected_customer_count=1200,
        sla_breach_count=25,
        negative_sentiment_ratio=0.7,
    )

    assessment = engine.analyze(incident, root_cause, trend, anomaly)

    assert assessment.incident_id == "INC-0042"
    assert assessment.root_cause == RootCause.SERVICE_OUTAGE
    assert assessment.financial_impact == ImpactLevel.CRITICAL
    assert assessment.customer_impact == ImpactLevel.CRITICAL
    assert assessment.operational_impact == ImpactLevel.CRITICAL
    assert assessment.sla_impact == ImpactLevel.CRITICAL
    assert assessment.reputation_impact == ImpactLevel.CRITICAL
    assert assessment.business_score == 100
    assert assessment.overall_severity == ImpactLevel.CRITICAL
    assert assessment.confidence == 100
    assert assessment.estimated_affected_customers == 1200
    assert "critical" in assessment.explanation


def test_engine_produces_none_assessment_when_no_signal_present(
    make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics
):
    engine = BusinessImpactEngine(rules=default_rules())
    # LOW severity is required here: FinancialRule treats the conftest
    # default of MEDIUM severity as its own (deliberate) MEDIUM signal.
    incident = make_incident(severity=AnomalySeverity.LOW)

    assessment = engine.analyze(incident, make_root_cause(), make_trend_metrics(), make_anomaly_metrics())

    assert assessment.business_score == 0
    assert assessment.overall_severity == ImpactLevel.NONE
    assert assessment.confidence == 0
    assert assessment.estimated_affected_customers == 0


def test_adding_a_new_rule_requires_no_engine_changes(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    rules = _stub_rules([ImpactLevel.HIGH] * 5)
    engine = BusinessImpactEngine(rules=rules)

    assessment = engine.analyze(make_incident(), make_root_cause(), make_trend_metrics(), make_anomaly_metrics())

    assert assessment.financial_impact == ImpactLevel.HIGH
    assert assessment.business_score == 75


def test_engine_raises_on_duplicate_dimension_evaluations(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    rules = [
        _StubRule(ImpactDimension.FINANCIAL, ImpactLevel.LOW),
        _StubRule(ImpactDimension.FINANCIAL, ImpactLevel.HIGH),
    ]
    engine = BusinessImpactEngine(rules=rules)

    with pytest.raises(ValueError, match="Duplicate"):
        engine.analyze(make_incident(), make_root_cause(), make_trend_metrics(), make_anomaly_metrics())


def test_engine_raises_on_missing_dimension_evaluations(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    rules = [_StubRule(ImpactDimension.FINANCIAL, ImpactLevel.LOW)]
    engine = BusinessImpactEngine(rules=rules)

    with pytest.raises(ValueError, match="Missing"):
        engine.analyze(make_incident(), make_root_cause(), make_trend_metrics(), make_anomaly_metrics())


def test_engine_is_deterministic_across_repeated_calls(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    engine = BusinessImpactEngine(rules=default_rules())
    incident = make_incident(severity=AnomalySeverity.HIGH)
    root_cause = make_root_cause(cause=RootCause.INVENTORY_SHORTAGE)
    trend = make_trend_metrics(percentage_change=20.0)
    anomaly = make_anomaly_metrics(affected_customer_count=150, sla_breach_count=4, negative_sentiment_ratio=0.2)

    first = engine.analyze(incident, root_cause, trend, anomaly)
    second = engine.analyze(incident, root_cause, trend, anomaly)

    assert first == second


def test_engine_never_mutates_its_inputs(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    engine = BusinessImpactEngine(rules=default_rules())
    incident = make_incident(regions=("us-east",))
    root_cause = make_root_cause()
    trend = make_trend_metrics()
    anomaly = make_anomaly_metrics()

    engine.analyze(incident, root_cause, trend, anomaly)

    assert incident.regions == ("us-east",)  # unchanged (frozen dataclass anyway)


def test_a_rule_never_receives_or_calls_another_rule():
    # ImpactRule.evaluate's signature only accepts plain input value objects
    # (Incident, RootCauseSummary, TrendMetrics, AnomalyMetrics) -- there is
    # no parameter through which one rule could reach another.
    import inspect

    signature = inspect.signature(ImpactRule.evaluate)
    param_names = list(signature.parameters.keys())
    assert param_names == ["self", "incident", "root_cause", "trend_metrics", "anomaly_metrics"]
