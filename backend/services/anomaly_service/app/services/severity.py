from typing import List, Literal, Optional, Tuple

from backend.shared.constants.enums.anomaly import AnomalySeverity

# Centralised, deterministic severity bands keyed to the magnitude of
# percentage change between a current and baseline window. Each entry is
# (upper_bound_inclusive, severity) — the magnitude falls in a band if it is
# less than or equal to that band's upper bound. The final band (CRITICAL)
# has no upper bound.
#
# Boundaries are inclusive on the lower-severity side (e.g. exactly 20.0%
# is NORMAL, not LOW) so that a "10 -> 12" style 20% change is not flagged
# as an anomaly.
SEVERITY_BANDS: List[Tuple[float, AnomalySeverity]] = [
    (20.0, AnomalySeverity.NORMAL),
    (50.0, AnomalySeverity.LOW),
    (100.0, AnomalySeverity.MEDIUM),
    (200.0, AnomalySeverity.HIGH),
]

# Change from a zero baseline has no finite ratio. Treated as the maximum
# severity band since any activity from nothing is a significant deviation.
UNDEFINED_BASELINE_SEVERITY = AnomalySeverity.CRITICAL


def compute_percentage_change(baseline: float, current: float) -> Optional[float]:
    """
    Returns the signed percentage change of `current` relative to `baseline`.

    Returns `None` when `baseline` is zero and `current` is non-zero — the
    ratio is undefined, not infinite-in-practice, and is treated as such
    throughout the pipeline (see `classify_severity`). Returns 0.0 when both
    are zero (no data, no change).
    """
    if baseline == 0:
        return None if current != 0 else 0.0
    return (current - baseline) / baseline * 100.0


def classify_severity(percentage_change: Optional[float]) -> AnomalySeverity:
    """
    Classifies the magnitude of a percentage change into a severity band.

    `percentage_change=None` represents a zero-baseline, non-zero-current
    comparison (undefined ratio) and is classified as CRITICAL. A change of
    exactly 0 (no data in either window, or no change at all) is NORMAL.
    """
    if percentage_change is None:
        return UNDEFINED_BASELINE_SEVERITY

    magnitude = abs(percentage_change)
    for upper_bound, severity in SEVERITY_BANDS:
        if magnitude <= upper_bound:
            return severity
    return AnomalySeverity.CRITICAL


def evaluate_change(
    baseline: float, current: float, direction: Literal["increase", "decrease"]
) -> Optional[Tuple[Optional[float], AnomalySeverity]]:
    """
    Evaluates whether a baseline -> current change in `direction`
    ("increase" or "decrease") is anomalous.

    Returns `None` when there is nothing to report: no data in either
    window, the change ran the wrong way for this detector's direction, or
    the magnitude falls within the NORMAL band. Otherwise returns
    `(percentage_change, severity)` for the caller to build a candidate from.
    """
    if baseline == 0 and current == 0:
        return None
    if direction == "increase" and current <= baseline:
        return None
    if direction == "decrease" and current >= baseline:
        return None

    pct = compute_percentage_change(baseline, current)
    severity = classify_severity(pct)
    if severity == AnomalySeverity.NORMAL:
        return None
    return pct, severity


def describe_rule(severity: AnomalySeverity, percentage_change: Optional[float]) -> str:
    """Returns a short, deterministic description of the rule that fired."""
    if percentage_change is None:
        return "undefined_baseline (zero baseline with new activity) -> CRITICAL"

    magnitude = abs(percentage_change)
    lower_bound = 0.0
    for upper_bound, band_severity in SEVERITY_BANDS:
        if band_severity == severity:
            return f"percentage_change magnitude {magnitude:.1f}% in ({lower_bound:.0f}%, {upper_bound:.0f}%] -> {severity.value.upper()}"
        lower_bound = upper_bound
    return f"percentage_change magnitude {magnitude:.1f}% > {lower_bound:.0f}% -> {severity.value.upper()}"
