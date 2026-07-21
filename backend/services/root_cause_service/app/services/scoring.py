# Centralised, deterministic point values for root-cause evidence.
# Every rule imports its point values from here rather than hardcoding
# them, so the whole scoring model can be tuned in one place — the same
# discipline used for anomaly severity (Phase 5 Step 2) and incident
# correlation confidence (Phase 5 Step 3).

CATEGORY_MATCH_POINTS = 40
CRITICAL_SEVERITY_POINTS = 25
HIGH_URGENCY_POINTS = 20
NEGATIVE_SENTIMENT_POINTS = 15
REGIONAL_SPIKE_POINTS = 15
VOLUME_SPIKE_POINTS = 10

MAX_SCORE = 100


def cap_score(raw_score: int) -> int:
    """Clamps a raw summed evidence score to the deterministic [0, MAX_SCORE] range."""
    return max(0, min(raw_score, MAX_SCORE))
