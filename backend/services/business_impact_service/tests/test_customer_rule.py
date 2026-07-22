from backend.services.business_impact_service.app.domain.impact_dimension import ImpactDimension
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.services.rules.customer_rule import CustomerRule
from backend.shared.constants.enums.complaint import UrgencyLabel


def test_none_when_no_customers_affected(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    incident = make_incident()
    anomaly = make_anomaly_metrics(affected_customer_count=0)

    result = CustomerRule().evaluate(incident, make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_dimension == ImpactDimension.CUSTOMER
    assert result.impact_level == ImpactLevel.NONE


def test_low_below_medium_threshold(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    anomaly = make_anomaly_metrics(affected_customer_count=42)

    result = CustomerRule().evaluate(make_incident(), make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.LOW


def test_medium_at_medium_threshold(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    anomaly = make_anomaly_metrics(affected_customer_count=100)

    result = CustomerRule().evaluate(make_incident(), make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.MEDIUM


def test_high_at_high_threshold(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    anomaly = make_anomaly_metrics(affected_customer_count=500)

    result = CustomerRule().evaluate(make_incident(), make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.HIGH


def test_critical_at_critical_threshold(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    anomaly = make_anomaly_metrics(affected_customer_count=1000)

    result = CustomerRule().evaluate(make_incident(), make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.CRITICAL


def test_high_urgency_escalates_by_one_level(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    incident = make_incident(urgency_levels=(UrgencyLabel.HIGH,))
    anomaly = make_anomaly_metrics(affected_customer_count=100)  # would be MEDIUM alone

    result = CustomerRule().evaluate(incident, make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.HIGH
    assert "escalated" in result.reason


def test_escalation_is_capped_at_critical(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    incident = make_incident(urgency_levels=(UrgencyLabel.CRITICAL,))
    anomaly = make_anomaly_metrics(affected_customer_count=1000)  # already CRITICAL

    result = CustomerRule().evaluate(incident, make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.CRITICAL


def test_high_urgency_does_not_escalate_when_no_customers_affected(
    make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics
):
    incident = make_incident(urgency_levels=(UrgencyLabel.CRITICAL,))
    anomaly = make_anomaly_metrics(affected_customer_count=0)

    result = CustomerRule().evaluate(incident, make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.NONE
