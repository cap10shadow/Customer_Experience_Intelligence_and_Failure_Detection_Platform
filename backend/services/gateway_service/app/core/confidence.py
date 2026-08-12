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
This module maps each stage's own band vocabulary independently: Root
Cause's via `band_to_confidence_level` (this function), Business
Impact's via `business_impact_band_to_confidence_level` (below) --
two separate functions over two separate dicts, deliberately never
sharing a code path even though both resolve to the same three-level
frontend vocabulary. business_impact_service's `confidence` measures a
completely different thing than Root Cause's (proportion of dimensions
with signal, not rule certainty; see business_impact_service/app/
domain/confidence.py), which is exactly why it required its own,
independently-derived thresholds rather than reusing these.

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


# business_impact_service now defines and exposes its own classification
# (Step 7.X A-05: backend/services/business_impact_service/app/domain/
# confidence.py -- "Low"/"Moderate"/"High", thresholds derived from the
# score's own proportional definition, never copied from Root Cause).
# This mapping is deliberately a SEPARATE dict and function from
# _ROOT_CAUSE_BAND_TO_LEVEL/band_to_confidence_level above -- ARB-008
# forbids the two stages from sharing a code path, even though both
# happen to map onto the same three-level frontend vocabulary.
_BUSINESS_IMPACT_BAND_TO_LEVEL = {
    "low": "low",
    "moderate": "moderate",
    "high": "high",
}


def business_impact_band_to_confidence_level(band: str) -> str:
    """Maps business_impact_service's own band string (case-insensitive) into the frontend's three-level ConfidenceLevel. Unrecognized bands map to 'low' rather than guessing upward. Business-Impact-specific -- see module docstring; never reused for Root Cause."""
    return _BUSINESS_IMPACT_BAND_TO_LEVEL.get(band.strip().lower(), "low")
