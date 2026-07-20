from typing import List

from backend.services.anomaly_service.app.models.anomaly import ActiveAnomaly
from backend.services.anomaly_service.app.services.scoring import RuleResult, SUPPORTING_SIGNAL_POINTS
from backend.shared.constants.enums.anomaly import AnomalyType

# A "primary" spike (volume/regional/category) reinforced by a "secondary"
# operational signal (urgency spike or sentiment deterioration) is a
# stronger correlation signal than either alone — e.g. Volume Spike +
# Urgency Spike + Negative Sentiment.
PRIMARY_SPIKE_TYPES = {AnomalyType.COMPLAINT_SPIKE, AnomalyType.REGIONAL_SPIKE, AnomalyType.CATEGORY_SPIKE}
SECONDARY_SIGNAL_TYPES = {AnomalyType.URGENCY_SPIKE, AnomalyType.SENTIMENT_SHIFT}


def evaluate(anomalies: List[ActiveAnomaly]) -> RuleResult:
    """
    Rule 5 — Supporting operational signals.

    Matches when the cluster contains at least one primary spike type
    (volume/regional/category) together with at least one secondary
    reinforcing signal (urgency spike or sentiment deterioration).
    """
    types = {a.type for a in anomalies}
    matched_primary = types & PRIMARY_SPIKE_TYPES
    matched_secondary = types & SECONDARY_SIGNAL_TYPES

    if matched_primary and matched_secondary:
        signals = sorted(t.value for t in (matched_primary | matched_secondary))
        return RuleResult(
            matched=True,
            points=SUPPORTING_SIGNAL_POINTS,
            reason=f"Supporting signals: {', '.join(signals)}",
        )
    return RuleResult(matched=False, points=0)
