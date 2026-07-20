from backend.services.anomaly_service.app.services.rules import supporting_signal_rule
from backend.shared.constants.enums.anomaly import AnomalyType


def test_volume_plus_urgency_matches(make_anomaly):
    anomalies = [
        make_anomaly(type=AnomalyType.COMPLAINT_SPIKE),
        make_anomaly(type=AnomalyType.URGENCY_SPIKE),
    ]
    result = supporting_signal_rule.evaluate(anomalies)
    assert result.matched is True
    assert result.points == 20


def test_volume_plus_sentiment_matches(make_anomaly):
    anomalies = [
        make_anomaly(type=AnomalyType.REGIONAL_SPIKE),
        make_anomaly(type=AnomalyType.SENTIMENT_SHIFT),
    ]
    result = supporting_signal_rule.evaluate(anomalies)
    assert result.matched is True


def test_only_primary_types_does_not_match(make_anomaly):
    anomalies = [
        make_anomaly(type=AnomalyType.COMPLAINT_SPIKE),
        make_anomaly(type=AnomalyType.REGIONAL_SPIKE),
    ]
    result = supporting_signal_rule.evaluate(anomalies)
    assert result.matched is False


def test_only_secondary_types_does_not_match(make_anomaly):
    anomalies = [
        make_anomaly(type=AnomalyType.URGENCY_SPIKE),
        make_anomaly(type=AnomalyType.SENTIMENT_SHIFT),
    ]
    result = supporting_signal_rule.evaluate(anomalies)
    assert result.matched is False
