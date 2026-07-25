from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ValidationSummary:
    """
    The ValidationEngine's verdict for one CompletedIntelligence snapshot.

    Acts as a precondition gate: when `is_valid` is False, the
    EvaluationOrchestrator returns this object directly as the "Validation
    Failure result" and never constructs an Evaluation -- QualityEngine,
    ExplainabilityEngine, and ConfidenceAnalyzer never run against
    structurally incomplete or malformed input.

    `reasons` is always empty when `is_valid` is True, and always carries at
    least one deterministic, human-readable reason when False -- never a
    bare boolean with no explanation, consistent with this platform's
    explainability-first philosophy.
    """
    is_valid: bool
    reasons: Tuple[str, ...] = ()
