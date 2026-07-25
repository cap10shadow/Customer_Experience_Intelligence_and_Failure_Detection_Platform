from backend.shared.constants.enums.base import BaseStringEnum


class EvaluationRating(BaseStringEnum):
    """
    Represents a deterministic, banded rating produced by the Evaluation
    Service's own engines (QualityEngine, ExplainabilityEngine).

    Service-local by design (mirrors the precedent set by
    `business_impact_service`'s `ImpactLevel`/`BusinessPriority`): the
    Evaluation Service is an independent Intelligence Assurance Service, so
    its rating vocabulary is its own and is never shared with or derived
    from another service's domain enums.
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
