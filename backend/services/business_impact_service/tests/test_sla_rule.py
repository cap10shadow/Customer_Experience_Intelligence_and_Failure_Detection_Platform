from backend.services.business_impact_service.app.domain.impact_dimension import ImpactDimension
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.services.rules.sla_rule import SLARule
from backend.shared.constants.enums.complaint import UrgencyLabel


def test_none_when_no_breaches(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    anomaly = make_anomaly_metrics(sla_breach_count=0)

    result = SLARule().evaluate(make_incident(), make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_dimension == ImpactDimension.SLA
    assert result.impact_level == ImpactLevel.NONE


def test_low_below_medium_threshold(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    anomaly = make_anomaly_metrics(sla_breach_count=1)

    result = SLARule().evaluate(make_incident(), make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.LOW


def test_medium_at_medium_threshold(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    anomaly = make_anomaly_metrics(sla_breach_count=3)

    result = SLARule().evaluate(make_incident(), make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.MEDIUM


def test_high_at_high_threshold(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    anomaly = make_anomaly_metrics(sla_breach_count=10)

    result = SLARule().evaluate(make_incident(), make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.HIGH


def test_critical_at_critical_threshold(make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics):
    anomaly = make_anomaly_metrics(sla_breach_count=20)

    result = SLARule().evaluate(make_incident(), make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.CRITICAL


def test_high_urgency_is_noted_in_reason_without_changing_level(
    make_incident, make_root_cause, make_trend_metrics, make_anomaly_metrics
):
    incident = make_incident(urgency_levels=(UrgencyLabel.CRITICAL,))
    anomaly = make_anomaly_metrics(sla_breach_count=1)

    result = SLARule().evaluate(incident, make_root_cause(), make_trend_metrics(), anomaly)

    assert result.impact_level == ImpactLevel.LOW
    assert "reinforced" in result.reason
