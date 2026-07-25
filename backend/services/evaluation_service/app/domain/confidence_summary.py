from dataclasses import dataclass


@dataclass(frozen=True)
class ConfidenceSummary:
    """
    The ConfidenceAnalyzer's summary of the confidence values already
    produced by upstream stages for one Incident.

    Per ADR-008, confidence is intentionally stage-specific: Root Cause's
    confidence measures certainty that the correct deterministic rule
    fired, while Business Impact's confidence measures completeness of
    available input data. This summary never blends those two distinct
    meanings into a new, invented confidence figure -- it preserves each
    stage's own value verbatim, and `average_confidence` is nothing more
    than the arithmetic mean of the two -- a transparent summary statistic,
    not a new assessment.
    """
    root_cause_confidence: int
    business_impact_confidence: int
    average_confidence: float
