from dataclasses import dataclass, field
from typing import List, Optional

# ----------------------------------------------------------------------
# Centralised, deterministic correlation configuration.
# Every rule module imports its point value from here rather than
# hardcoding it, so the whole scoring model can be tuned in one place.
# ----------------------------------------------------------------------

REGION_POINTS = 25
CATEGORY_POINTS = 20
TIME_WINDOW_POINTS = 20
SEVERITY_POINTS = 15
SUPPORTING_SIGNAL_POINTS = 20

MAX_CONFIDENCE = REGION_POINTS + CATEGORY_POINTS + TIME_WINDOW_POINTS + SEVERITY_POINTS + SUPPORTING_SIGNAL_POINTS  # 100

# Default correlation time window. Configurable per run via the API.
DEFAULT_TIME_WINDOW_MINUTES = 15

# A cluster must reach at least this score to become (or update) an
# Incident. Below this, anomalies are considered too weakly related to
# justify grouping them — "Weak" (0-30) is not itself an incident signal.
MIN_CONFIDENCE_TO_CORRELATE = 31

# (upper_bound_inclusive, band_name)
CONFIDENCE_BANDS = [
    (30, "Weak"),
    (60, "Possible"),
    (80, "Strong"),
]
# > 80 -> "Very Strong"


@dataclass(frozen=True)
class RuleResult:
    """One correlation rule's verdict for a candidate cluster of anomalies."""
    matched: bool
    points: int
    reason: Optional[str] = None


@dataclass(frozen=True)
class ConfidenceScore:
    """The combined outcome of every rule for one candidate cluster."""
    score: int
    band: str
    reasons: List[str] = field(default_factory=list)


def classify_band(score: int) -> str:
    for upper_bound, band in CONFIDENCE_BANDS:
        if score <= upper_bound:
            return band
    return "Very Strong"


def combine(rule_results: List[RuleResult]) -> ConfidenceScore:
    """Sums matched rules' points (capped at MAX_CONFIDENCE) and collects their reasons."""
    score = min(sum(r.points for r in rule_results if r.matched), MAX_CONFIDENCE)
    reasons = [r.reason for r in rule_results if r.matched and r.reason]
    return ConfidenceScore(score=score, band=classify_band(score), reasons=reasons)
