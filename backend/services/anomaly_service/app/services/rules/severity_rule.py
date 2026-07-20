from typing import List

from backend.services.anomaly_service.app.models.anomaly import ActiveAnomaly
from backend.services.anomaly_service.app.services.scoring import RuleResult, SEVERITY_POINTS


def evaluate(anomalies: List[ActiveAnomaly]) -> RuleResult:
    """
    Rule 4 — Shared severity.

    Matches when every anomaly in the cluster carries the same severity.
    """
    if len(anomalies) < 2:
        return RuleResult(matched=False, points=0)

    severities = {a.severity for a in anomalies}
    if len(severities) == 1:
        severity = next(iter(severities))
        return RuleResult(matched=True, points=SEVERITY_POINTS, reason=f"Same severity ({severity.value})")
    return RuleResult(matched=False, points=0)
