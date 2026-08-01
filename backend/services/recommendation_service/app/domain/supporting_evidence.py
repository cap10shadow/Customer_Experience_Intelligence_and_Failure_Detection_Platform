from dataclasses import dataclass

from backend.services.recommendation_service.app.domain.evidence_source import EvidenceSource


@dataclass(frozen=True)
class SupportingEvidence:
    """
    A single, structured, explainable fact from the `IntelligenceContext`
    that contributed to a Recommendation. Never a plain string -- every
    piece of evidence carries its source and point weight, so the shared
    Recommendation Scoring Policy (`scoring.py`) has no hidden inputs and
    the final rationale has no uncredited calculations. The same
    discipline Root Cause Service's `Evidence` already established.
    """

    source: EvidenceSource
    description: str
    weight: int
