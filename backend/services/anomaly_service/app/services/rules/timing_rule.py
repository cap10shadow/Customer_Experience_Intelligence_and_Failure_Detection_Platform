from datetime import timedelta
from typing import List

from backend.services.anomaly_service.app.models.anomaly import ActiveAnomaly
from backend.services.anomaly_service.app.services.scoring import RuleResult, TIME_WINDOW_POINTS


def evaluate(anomalies: List[ActiveAnomaly], window_minutes: int) -> RuleResult:
    """
    Rule 1 — Temporal proximity.

    Matches when every anomaly in the cluster was first detected within
    `window_minutes` of each other (span of first_detected_at <= window).
    """
    if len(anomalies) < 2:
        return RuleResult(matched=False, points=0)

    timestamps = [a.first_detected_at for a in anomalies]
    span = max(timestamps) - min(timestamps)
    if span <= timedelta(minutes=window_minutes):
        return RuleResult(
            matched=True,
            points=TIME_WINDOW_POINTS,
            reason=f"{len(anomalies)} anomalies within {window_minutes} minutes",
        )
    return RuleResult(matched=False, points=0)
