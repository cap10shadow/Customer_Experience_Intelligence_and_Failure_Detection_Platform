from dataclasses import dataclass
from typing import List, Tuple

# Centralised, deterministic confidence bands — the same scoring philosophy
# established for anomaly severity (Phase 5 Step 2) and incident
# correlation confidence (Phase 5 Step 3): a fixed list of
# (upper_bound_inclusive, band) pairs, magnitude-based, no probabilistic
# reasoning.
CONFIDENCE_BANDS: List[Tuple[int, str]] = [
    (30, "Weak"),
    (50, "Low"),
    (70, "Medium"),
    (90, "High"),
]
# > 90 -> "Very High"


def classify_confidence(score: int) -> str:
    """Classifies a 0-100 confidence score into its band."""
    for upper_bound, band in CONFIDENCE_BANDS:
        if score <= upper_bound:
            return band
    return "Very High"


@dataclass(frozen=True)
class ConfidenceScore:
    """A confidence score paired with its deterministic band."""
    score: int
    band: str

    @classmethod
    def from_score(cls, score: int) -> "ConfidenceScore":
        """Clamps `score` to [0, 100] and classifies it in one step."""
        clamped = max(0, min(score, 100))
        return cls(score=clamped, band=classify_confidence(clamped))
