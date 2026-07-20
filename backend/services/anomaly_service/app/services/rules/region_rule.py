from typing import List

from backend.services.anomaly_service.app.models.anomaly import ActiveAnomaly
from backend.services.anomaly_service.app.services.scoring import RuleResult, REGION_POINTS


def evaluate(anomalies: List[ActiveAnomaly]) -> RuleResult:
    """
    Rule 2 — Same region.

    Matches when at least two region-scoped anomalies in the cluster
    (entity_type == "region") share the same entity_value. Anomalies that
    are not region-scoped simply don't participate in this rule.
    """
    regions = [a.entity_value for a in anomalies if a.entity_type == "region" and a.entity_value]
    if len(regions) >= 2 and len(set(regions)) == 1:
        return RuleResult(matched=True, points=REGION_POINTS, reason=f"Same region ({regions[0]})")
    return RuleResult(matched=False, points=0)
