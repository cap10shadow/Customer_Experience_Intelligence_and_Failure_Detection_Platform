from dataclasses import dataclass
from typing import List, Tuple

# Business-Impact-owned confidence classification (Step 7.X A-05).
#
# ARB-008 (docs/DECISIONS.md, "Confidence Remains Stage-Specific"): this
# module must never reuse root_cause_service's confidence bands
# (backend/services/root_cause_service/app/domain/confidence.py) or its
# threshold values (30/50/70/90). Root Cause's confidence measures
# certainty that the correct deterministic rule fired; Business Impact's
# confidence measures something entirely different -- see
# scoring.compute_confidence's own docstring: "the proportion of the five
# impact dimensions that carried an actual signal (non-NONE) rather than
# a default, uninformative reading... NOT a probability or ML estimate --
# purely a measure of how complete the available intelligence was."
#
# Threshold rationale (why these boundaries are defensible, not arbitrary):
# compute_confidence() can only ever produce one of exactly six values --
# round((informative / 5) * 100) for informative in 0..5, i.e.
# 0, 20, 40, 60, 80, 100. Because the score IS a proportion of five
# discrete dimensions, the only threshold split groundable in the score's
# own definition (rather than an arbitrary numeric pick) is a completeness
# majority: fewer than half the dimensions informative (0-2 of 5) is "Low"
# confidence in the assessment's completeness; a majority but not all
# (3-4 of 5) is "Moderate"; every dimension informative (5 of 5) is
# "High". No boundary here was copied from another stage or invented
# independently of the score's own proportional meaning.
CONFIDENCE_BANDS: List[Tuple[int, str]] = [
    (40, "Low"),  # 0/5 or 1/5 or 2/5 dimensions informative
    (80, "Moderate"),  # 3/5 or 4/5 dimensions informative
]
# 100 (5/5 dimensions informative) -> "High"


def classify_confidence(score: int) -> str:
    """Classifies a 0-100 Business Impact confidence score into its band. Business-Impact-specific -- see module docstring; never reused for another stage's confidence value."""
    for upper_bound, band in CONFIDENCE_BANDS:
        if score <= upper_bound:
            return band
    return "High"


@dataclass(frozen=True)
class ConfidenceScore:
    """A Business Impact confidence score paired with its deterministic, Business-Impact-owned band."""

    score: int
    band: str

    @classmethod
    def from_score(cls, score: int) -> "ConfidenceScore":
        """Clamps `score` to [0, 100] and classifies it in one step."""
        clamped = max(0, min(score, 100))
        return cls(score=clamped, band=classify_confidence(clamped))
