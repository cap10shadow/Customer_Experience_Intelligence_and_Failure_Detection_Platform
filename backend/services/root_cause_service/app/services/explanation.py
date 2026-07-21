from typing import Tuple

from backend.services.root_cause_service.app.domain.evidence import Evidence
from backend.services.root_cause_service.app.services.rule_engine import RuleResult


def build_explanation(result: RuleResult, evidence: Tuple[Evidence, ...], confidence_band: str) -> str:
    """
    Formats a human-readable explanation for the selected RuleResult.

    Pure formatting only — every reason shown here was already decided by
    the rule that produced `result`; this function invents nothing.
    """
    if not evidence:
        return f"No deterministic rule matched this incident (confidence: {result.score}, {confidence_band})."

    reasons = "; ".join(evidence_item.description for evidence_item in evidence)
    return (
        f"{result.cause.value} identified with {result.score} confidence ({confidence_band}). "
        f"Reasons: {reasons}."
    )


def build_unknown_explanation() -> str:
    return "No deterministic rule matched this incident; root cause is unknown."
