from backend.services.business_impact_service.app.domain.impact_dimension import ImpactDimension
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.services.rules.operational_rule import OperationalRule
from backend.shared.constants.enums.anomaly import AnomalySeverity
from backend.shared.constants.enums.root_cause import RootCause


def test_none_when_cause_is_not_operational_and_severity_is_normal(
    make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics
):
    root_cause = make_root_cause(cause=RootCause.PAYMENT_GATEWAY_FAILURE)
    anomaly = make_anomaly_metrics(severity=AnomalySeverity.LOW)

    result = OperationalRule().evaluate(make_incident(), root_cause, make_trend_metrics(), anomaly)

    assert result.impact_dimension == ImpactDimension.OPERATIONAL
    assert result.impact_level == ImpactLevel.NONE


def test_low_on_elevated_severity_without_operational_cause(
    make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics
):
    root_cause = make_root_cause(cause=RootCause.CUSTOMER_SUPPORT_DELAY)
    anomaly = make_anomaly_metrics(severity=AnomalySeverity.HIGH)

    result = OperationalRule().evaluate(make_incident(), root_cause, make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.LOW


def test_medium_on_operational_cause_with_normal_severity(
    make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics
):
    root_cause = make_root_cause(cause=RootCause.SERVICE_OUTAGE)
    anomaly = make_anomaly_metrics(severity=AnomalySeverity.LOW)

    result = OperationalRule().evaluate(make_incident(), root_cause, make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.MEDIUM


def test_high_on_operational_cause_with_high_severity(
    make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics
):
    root_cause = make_root_cause(cause=RootCause.INVENTORY_SHORTAGE)
    anomaly = make_anomaly_metrics(severity=AnomalySeverity.HIGH)

    result = OperationalRule().evaluate(make_incident(), root_cause, make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.HIGH


def test_critical_on_operational_cause_with_critical_severity(
    make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics
):
    root_cause = make_root_cause(cause=RootCause.SERVICE_OUTAGE)
    anomaly = make_anomaly_metrics(severity=AnomalySeverity.CRITICAL)

    result = OperationalRule().evaluate(make_incident(), root_cause, make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.CRITICAL


def test_unknown_root_cause_is_never_treated_as_operational(
    make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics
):
    root_cause = make_root_cause(cause=RootCause.UNKNOWN)
    anomaly = make_anomaly_metrics(severity=AnomalySeverity.CRITICAL)

    result = OperationalRule().evaluate(make_incident(), root_cause, make_trend_metrics(), anomaly)

    # UNKNOWN + CRITICAL anomaly severity falls back to the elevated-severity LOW path.
    assert result.impact_level == ImpactLevel.LOW
