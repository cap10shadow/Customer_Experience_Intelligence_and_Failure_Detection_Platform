from typing import List, Literal, Optional

from pydantic import BaseModel


class SupportingEvidenceDTO(BaseModel):
    source: str
    description: str
    weight: int


# Step 7.X G-01: the same four values recommendation_service's own
# RecommendationDecision enum defines. Kept as a plain Literal here
# (Gateway does not import a backend service's domain enum -- DATA-002)
# rather than a shared type.
RecommendationDecisionValue = Literal["pending", "approved", "rejected", "deferred"]


class RecommendationResponse(BaseModel):
    """
    Public Gateway DTO for GET /api/v1/recommendations/{recommendationId} --
    a single-service read (recommendation_service), not a multi-service
    aggregation like Investigation. Every field here maps 1:1 to a real
    recommendation_service field (see RecommendationDetailResponse); the
    Gateway performs no calculation and adds nothing recommendation_service
    doesn't already provide (Batch 4A SS8/SS10).

    Fields recommendation_service does not provide today -- confidence,
    alternatives, risk, expected outcome -- are deliberately absent from
    this DTO rather than represented as null, since a present-but-null
    field would still imply the concept exists on the backend. See Part
    4's implementation report for the full field audit.

    `decision`/`decisionNote`/`decidedAt` (Step 7.X G-01) are the one
    addition since then -- additive only, all Optional/None until a real
    decision is persisted; no actor/owner field, matching
    recommendation_service's own DTO.
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
    decision: Optional[RecommendationDecisionValue] = None
    decisionNote: Optional[str] = None
    decidedAt: Optional[str] = None


class RecommendationDecisionPatchRequest(BaseModel):
    """
    Request body for `PATCH /api/v1/recommendations/{recommendationId}/decision`
    (Step 7.X G-01). Mirrors recommendation_service's own request shape
    exactly -- the Gateway performs no transformation, only forwards.
    Deliberately excludes any actor/owner/timestamp field: `decidedAt` is
    always server-set, downstream.
    """

    decision: RecommendationDecisionValue
    note: Optional[str] = None
