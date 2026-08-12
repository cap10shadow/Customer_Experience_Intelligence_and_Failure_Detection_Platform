from typing import List

from pydantic import BaseModel


class SupportingEvidenceDTO(BaseModel):
    source: str
    description: str
    weight: int


class RecommendationResponse(BaseModel):
    """
    Public Gateway DTO for GET /api/v1/recommendations/{recommendationId} --
    a single-service read (recommendation_service), not a multi-service
    aggregation like Investigation. Every field here maps 1:1 to a real
    recommendation_service field (see RecommendationDetailResponse); the
    Gateway performs no calculation and adds nothing recommendation_service
    doesn't already provide (Batch 4A SS8/SS10).

    Fields recommendation_service does not provide today -- confidence,
    alternatives, risk, expected outcome, decision/lifecycle state -- are
    deliberately absent from this DTO rather than represented as null,
    since a present-but-null field would still imply the concept exists on
    the backend. See Part 4's implementation report for the full field
    audit.
    """

    recommendationId: str
    incidentId: str
    generationId: str
    category: str
    priority: str
    score: int
    action: str
    recommendationRationale: str
    priorityRationale: str
    supportingEvidence: List[SupportingEvidenceDTO] = []
    createdAt: str
