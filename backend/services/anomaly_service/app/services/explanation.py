from typing import List

from backend.services.anomaly_service.app.models.anomaly import ActiveAnomaly
from backend.services.anomaly_service.app.services.scoring import ConfidenceScore


def build_summary(anomalies: List[ActiveAnomaly], confidence: ConfidenceScore) -> str:
    """
    Builds the human-readable incident summary directly from the rule
    outcomes that produced the confidence score — no hidden logic, matching
    the same explainability standard as ActiveAnomaly.explanation.
    """
    reasons = "; ".join(confidence.reasons) if confidence.reasons else "no reinforcing correlation signals"
    return (
        f"{len(anomalies)} correlated anomalies. "
        f"Confidence: {confidence.score} ({confidence.band}). "
        f"Reasons: {reasons}."
    )


def build_resolved_reason() -> str:
    return "All linked anomalies have been resolved."
