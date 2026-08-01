from backend.shared.constants.enums.base import BaseStringEnum


class EvidenceSource(BaseStringEnum):
    """
    Represents which slice of the `IntelligenceContext` a single piece of
    `SupportingEvidence` was drawn from -- the same explainability role
    Root Cause Service's `EvidenceType` plays for its own `Evidence`
    objects, applied here to the five constituents of `IntelligenceContext`
    instead of root-cause dimensions.
    """

    INCIDENT = "incident"
    BUSINESS_IMPACT = "business_impact"
    ROOT_CAUSE = "root_cause"
    NLP_INTELLIGENCE = "nlp_intelligence"
    ANOMALY_INTELLIGENCE = "anomaly_intelligence"
