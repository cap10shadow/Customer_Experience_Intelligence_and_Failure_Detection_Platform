from typing import List

from backend.services.anomaly_service.app.models.anomaly import ActiveAnomaly
from backend.services.anomaly_service.app.services.scoring import RuleResult, CATEGORY_POINTS


def evaluate(anomalies: List[ActiveAnomaly]) -> RuleResult:
    """
    Rule 3 — Same category.

    Matches when at least two category-scoped anomalies in the cluster
    (entity_type == "category") share the same entity_value.
    """
    categories = [a.entity_value for a in anomalies if a.entity_type == "category" and a.entity_value]
    if len(categories) >= 2 and len(set(categories)) == 1:
        return RuleResult(matched=True, points=CATEGORY_POINTS, reason=f"Same category ({categories[0]})")
    return RuleResult(matched=False, points=0)
