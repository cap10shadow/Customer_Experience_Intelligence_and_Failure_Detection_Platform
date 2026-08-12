from typing import List, Literal, Optional

from pydantic import BaseModel

# Mirrors frontend/src/workspaces/investigations/types.ts's vocabulary exactly.
ConfidenceLevel = Literal["low", "moderate", "high"]
EvidenceSource = Literal["NLP Intelligence", "Anomaly Detection", "Incident Correlation", "Root Cause Analysis"]
BusinessImpactDimension = Literal["financial", "customer", "operational", "sla", "reputation"]


class ObservationDTO(BaseModel):
    headline: str
    description: str


class EvidenceItemDTO(BaseModel):
    id: str
    headline: str
    detail: str
    source: EvidenceSource


class RootCauseExplanationDTO(BaseModel):
    headline: str
    reasoning: str
    confidenceLevel: ConfidenceLevel


class BusinessImpactDimensionSummaryDTO(BaseModel):
    dimension: BusinessImpactDimension
    headline: str
    detail: str


class RecommendedActionDTO(BaseModel):
    headline: str
    reason: str
    recommendationId: Optional[str] = None


class InvestigationResponse(BaseModel):
    incidentId: str
    observation: ObservationDTO
    evidence: List[EvidenceItemDTO]
    # None means "not yet analyzed" (root_cause_service 404) -- a real
    # domain state, not a failure. Never fabricated.
    rootCause: Optional[RootCauseExplanationDTO] = None
    # Empty means "not yet assessed" (business_impact_service 404/empty) --
    # same principle. Never padded to five entries with invented content.
    businessImpact: List[BusinessImpactDimensionSummaryDTO] = []
    # Always None today: business_impact_service exposes only a raw
    # confidence int with no stage-specific band classification of its
    # own, and ARB-008 (Confidence Remains Stage-Specific) forbids the
    # Gateway from inventing one -- in particular, forbids reusing
    # root_cause_service's confidence bands, which are Root-Cause-domain
    # semantics, not a portable platform scale. Populated only once
    # business_impact_service defines and exposes its own classification
    # (a Step 7.X capability, not a Gateway concern).
    businessImpactConfidenceLevel: Optional[ConfidenceLevel] = None
    recommendedNextStep: Optional[RecommendedActionDTO] = None
    # Human-readable notes about any non-essential downstream source that
    # was unavailable when this response was built. Empty when everything
    # succeeded (a None rootCause/empty businessImpact from a genuine 404
    # is NOT a warning -- see the aggregator's essential/non-essential
    # classification).
    warnings: List[str] = []
