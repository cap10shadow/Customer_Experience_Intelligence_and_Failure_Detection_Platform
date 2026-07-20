from backend.services.anomaly_service.app.services.rules import severity_rule
from backend.shared.constants.enums.anomaly import AnomalySeverity


def test_matching_severity_matches(make_anomaly):
    anomalies = [
        make_anomaly(severity=AnomalySeverity.CRITICAL),
        make_anomaly(severity=AnomalySeverity.CRITICAL),
    ]
    result = severity_rule.evaluate(anomalies)
    assert result.matched is True
    assert result.points == 15
    assert "critical" in result.reason


def test_differing_severity_does_not_match(make_anomaly):
    anomalies = [
        make_anomaly(severity=AnomalySeverity.CRITICAL),
        make_anomaly(severity=AnomalySeverity.LOW),
    ]
    result = severity_rule.evaluate(anomalies)
    assert result.matched is False


def test_single_anomaly_does_not_match(make_anomaly):
    result = severity_rule.evaluate([make_anomaly()])
    assert result.matched is False
