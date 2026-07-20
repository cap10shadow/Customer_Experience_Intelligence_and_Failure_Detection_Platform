from datetime import datetime, timedelta, timezone

from backend.services.anomaly_service.app.services.rules import timing_rule


def test_within_window_matches(make_anomaly):
    base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
    anomalies = [
        make_anomaly(first_detected_at=base),
        make_anomaly(first_detected_at=base + timedelta(minutes=10)),
    ]
    result = timing_rule.evaluate(anomalies, window_minutes=15)
    assert result.matched is True
    assert result.points == 20
    assert "2 anomalies within 15 minutes" in result.reason


def test_outside_window_does_not_match(make_anomaly):
    base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
    anomalies = [
        make_anomaly(first_detected_at=base),
        make_anomaly(first_detected_at=base + timedelta(minutes=20)),
    ]
    result = timing_rule.evaluate(anomalies, window_minutes=15)
    assert result.matched is False
    assert result.points == 0


def test_single_anomaly_never_matches(make_anomaly):
    result = timing_rule.evaluate([make_anomaly()], window_minutes=15)
    assert result.matched is False


def test_three_weeks_apart_does_not_match(make_anomaly):
    base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
    anomalies = [
        make_anomaly(first_detected_at=base),
        make_anomaly(first_detected_at=base - timedelta(weeks=3)),
    ]
    result = timing_rule.evaluate(anomalies, window_minutes=15)
    assert result.matched is False
