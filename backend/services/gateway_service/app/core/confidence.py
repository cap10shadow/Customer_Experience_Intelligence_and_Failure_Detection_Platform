"""
Root Cause confidence-band -> frontend ConfidenceLevel mapping.

root_cause_service classifies its 0-100 confidence_score into one of
"Weak"/"Low"/"Medium"/"High"/"Very High" bands using its own fixed,
domain-specific thresholds (backend/services/root_cause_service/app/
domain/confidence.py: CONFIDENCE_BANDS = [(30,"Weak"),(50,"Low"),
(70,"Medium"),(90,"High")], >90 -> "Very High").

ARB-008 (docs/DECISIONS.md, "Confidence Remains Stage-Specific"):
confidence is produced by multiple stages with materially different
meanings, and each service owns its own confidence definition -- the
architecture explicitly does NOT force one universal confidence score.
This module therefore maps ONLY root_cause_service's own band
vocabulary; it must not be reused for any other service's confidence
value (business_impact_service's `confidence`, for example, measures a
completely different thing -- proportion of dimensions with signal --
and has no band classifier of its own, so its Gateway DTO field is
None until that service defines and exposes one itself).

The Investigation frontend's ConfidenceLevel ('low'|'moderate'|'high')
is a shared *presentation* vocabulary only, coarser than any one stage's
own bands -- it does not authorize borrowing one stage's threshold
values to classify a different stage's differently-computed number.
"""

_ROOT_CAUSE_BAND_TO_LEVEL = {
    "weak": "low",
    "low": "low",
    "medium": "moderate",
    "high": "high",
    "very high": "high",
}


def band_to_confidence_level(band: str) -> str:
    """Maps root_cause_service's own band string (case-insensitive) into the frontend's three-level ConfidenceLevel. Unrecognized bands map to 'low' rather than guessing upward. Root Cause-specific -- see module docstring."""
    return _ROOT_CAUSE_BAND_TO_LEVEL.get(band.strip().lower(), "low")
