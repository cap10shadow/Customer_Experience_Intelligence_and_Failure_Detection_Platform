# Recommendation Scoring Policy -- the one shared, centralized scoring
# methodology every Recommendation Rule must call into (never hardcode its
# own arithmetic). The ARB review identified cross-rule score inconsistency
# as a risk; the frozen mitigation is exactly this: no post-processing
# normalizer, every rule computes its score using this same policy, which
# guarantees consistency by construction rather than by correction. The
# same centralized-constants discipline already established by Business
# Impact's `scoring.py`/`weighting.py` and Root Cause's `scoring.py`.

from typing import Dict, Sequence

from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.supporting_evidence import SupportingEvidence

# Deterministic base score per priority tier. Priority and score remain
# intentionally separate concepts (frozen architecture) -- this base is a
# starting point every rule shares, not a derivation of one from the other;
# a rule's own supporting evidence still moves the final score.
BASE_SCORE_BY_PRIORITY: Dict[RecommendationPriority, int] = {
    RecommendationPriority.CRITICAL: 70,
    RecommendationPriority.HIGH: 55,
    RecommendationPriority.MEDIUM: 40,
    RecommendationPriority.LOW: 25,
}

MIN_SCORE = 0
MAX_SCORE = 100


def compute_score(priority: RecommendationPriority, supporting_evidence: Sequence[SupportingEvidence]) -> int:
    """
    Computes a Recommendation's deterministic score (0-100): the priority
    tier's base score, plus the sum of every piece of supporting evidence's
    weight, clamped to the valid range. Every Recommendation Rule -- and
    `RecommendationConsolidator` when merging equivalent recommendations --
    calls this same function, never its own scoring arithmetic.
    """
    base = BASE_SCORE_BY_PRIORITY[priority]
    evidence_contribution = sum(evidence.weight for evidence in supporting_evidence)
    return _clamp(base + evidence_contribution)


def _clamp(value: int) -> int:
    return max(MIN_SCORE, min(value, MAX_SCORE))
