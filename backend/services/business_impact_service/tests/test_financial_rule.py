from backend.services.business_impact_service.app.domain.impact_dimension import ImpactDimension
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.services.rules.financial_rule import FinancialRule
from backend.shared.constants.enums.anomaly import AnomalySeverity


def test_none_when_no_severity_or_volume_signal(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    incident = make_incident(severity=AnomalySeverity.LOW)
    trend = make_trend_metrics(percentage_change=0.0)

    result = FinancialRule().evaluate(incident, make_root_cause(), trend, make_anomaly_metrics())

    assert result.impact_dimension == ImpactDimension.FINANCIAL
    assert result.impact_level == ImpactLevel.NONE


def test_low_on_small_volume_increase_alone(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    incident = make_incident(severity=AnomalySeverity.LOW)
    trend = make_trend_metrics(percentage_change=5.0)

    result = FinancialRule().evaluate(incident, make_root_cause(), trend, make_anomaly_metrics())

    assert result.impact_level == ImpactLevel.LOW


def test_medium_on_medium_severity_alone(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    incident = make_incident(severity=AnomalySeverity.MEDIUM)
    trend = make_trend_metrics(percentage_change=0.0)

    result = FinancialRule().evaluate(incident, make_root_cause(), trend, make_anomaly_metrics())

    assert result.impact_level == ImpactLevel.MEDIUM


def test_high_on_high_severity_alone(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    incident = make_incident(severity=AnomalySeverity.HIGH)
    trend = make_trend_metrics(percentage_change=0.0)

    result = FinancialRule().evaluate(incident, make_root_cause(), trend, make_anomaly_metrics())

    assert result.impact_level == ImpactLevel.HIGH


def test_high_on_large_volume_increase_alone(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    incident = make_incident(severity=AnomalySeverity.LOW)
    trend = make_trend_metrics(percentage_change=35.0)

    result = FinancialRule().evaluate(incident, make_root_cause(), trend, make_anomaly_metrics())

    assert result.impact_level == ImpactLevel.HIGH


def test_critical_requires_both_critical_severity_and_large_volume_increase(
    make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics
):
    incident = make_incident(severity=AnomalySeverity.CRITICAL)
    trend = make_trend_metrics(percentage_change=60.0)

    result = FinancialRule().evaluate(incident, make_root_cause(), trend, make_anomaly_metrics())

    assert result.impact_level == ImpactLevel.CRITICAL


def test_critical_severity_alone_without_volume_spike_is_only_high(
    make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics
):
    incident = make_incident(severity=AnomalySeverity.CRITICAL)
    trend = make_trend_metrics(percentage_change=0.0)

    result = FinancialRule().evaluate(incident, make_root_cause(), trend, make_anomaly_metrics())

    assert result.impact_level == ImpactLevel.HIGH


def test_is_deterministic_across_repeated_calls(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    incident = make_incident(severity=AnomalySeverity.HIGH)
    trend = make_trend_metrics(percentage_change=10.0)
    root_cause = make_root_cause()
    anomaly = make_anomaly_metrics()

    first = FinancialRule().evaluate(incident, root_cause, trend, anomaly)
    second = FinancialRule().evaluate(incident, root_cause, trend, anomaly)

    assert first == second
