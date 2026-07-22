from backend.services.business_impact_service.app.domain.impact_dimension import ImpactDimension
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.services.rules.reputation_rule import ReputationRule
from backend.shared.constants.enums.anomaly import AnomalyType


def test_none_when_no_negative_sentiment(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    anomaly = make_anomaly_metrics(negative_sentiment_ratio=0.0)

    result = ReputationRule().evaluate(make_incident(), make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_dimension == ImpactDimension.REPUTATION
    assert result.impact_level == ImpactLevel.NONE


def test_low_below_medium_ratio(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    anomaly = make_anomaly_metrics(negative_sentiment_ratio=0.1)

    result = ReputationRule().evaluate(make_incident(), make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.LOW


def test_medium_at_medium_ratio(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    anomaly = make_anomaly_metrics(negative_sentiment_ratio=0.3)

    result = ReputationRule().evaluate(make_incident(), make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.MEDIUM


def test_high_at_high_ratio(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    anomaly = make_anomaly_metrics(negative_sentiment_ratio=0.6)

    result = ReputationRule().evaluate(make_incident(), make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.HIGH


def test_confirmed_sentiment_shift_escalates_by_one_level(
    make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics
):
    anomaly = make_anomaly_metrics(negative_sentiment_ratio=0.3, anomaly_types=(AnomalyType.SENTIMENT_SHIFT,))

    result = ReputationRule().evaluate(make_incident(), make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.HIGH
    assert "confirmed by a sentiment-shift anomaly" in result.reason


def test_multi_region_spread_escalates_by_one_level(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    incident = make_incident(regions=("us-east", "us-west"))
    anomaly = make_anomaly_metrics(negative_sentiment_ratio=0.3)

    result = ReputationRule().evaluate(incident, make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.HIGH
    assert "spanning 2 regions" in result.reason


def test_both_reinforcing_signals_stack_and_cap_at_critical(
    make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics
):
    incident = make_incident(regions=("us-east", "us-west", "eu"))
    anomaly = make_anomaly_metrics(negative_sentiment_ratio=0.6, anomaly_types=(AnomalyType.SENTIMENT_SHIFT,))

    result = ReputationRule().evaluate(incident, make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.CRITICAL


def test_single_region_does_not_trigger_multi_region_escalation(
    make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics
):
    incident = make_incident(regions=("us-east",))
    anomaly = make_anomaly_metrics(negative_sentiment_ratio=0.3)

    result = ReputationRule().evaluate(incident, make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.MEDIUM
