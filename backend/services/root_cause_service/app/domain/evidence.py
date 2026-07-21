from dataclasses import dataclass

from backend.shared.constants.enums.base import BaseStringEnum


class EvidenceType(BaseStringEnum):
    """Represents the dimension a piece of root-cause evidence speaks to."""
    CATEGORY = "category"
    SEVERITY = "severity"
    URGENCY = "urgency"
    SENTIMENT = "sentiment"
    REGION = "region"
    SUPPORTING_SIGNAL = "supporting_signal"


@dataclass(frozen=True)
class Evidence:
    """
    A single, structured, explainable fact that contributed to a rule's
    score. Never a plain string — every piece of evidence carries its
    dimension and point weight so the final explanation has no hidden
    calculations.
    """
    type: EvidenceType
    description: str
    weight: int
