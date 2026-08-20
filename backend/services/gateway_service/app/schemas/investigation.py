from typing import List, Literal, Optional

from pydantic import BaseModel

# Mirrors frontend/src/workspaces/investigations/types.ts's vocabulary exactly.
ConfidenceLevel = Literal["low", "moderate", "high"]
EvidenceSource = Literal["NLP Intelligence", "Anomaly Detection", "Incident Correlation", "Root Cause Analysis"]
BusinessImpactDimension = Literal["financial", "customer", "operational", "sla", "reputation"]
# Mirrors root_cause_service's own RootCauseStatus enum exactly (Gateway
# does not import a backend service's domain enum -- DATA-002, the same
# convention schemas/recommendations.py's RecommendationDecisionValue
# documents).
RootCauseLifecycleStatus = Literal["identified", "confirmed", "rejected"]


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
    # Additive field: root_cause_service already exposes this (its own
    # RootCauseStatus), previously dropped by `_build_root_cause` even
    # though the Investigation's RootCauseAnalysis section now offers
    # real confirm/reject/refresh actions that need to know the current
    # lifecycle state to render sensibly (e.g. not offering "Confirm"
    # again once already confirmed).
    status: RootCauseLifecycleStatus


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
    # AD-12 follow-up: the Incident this Investigation is built from
    # already carries a real `dataset_id` (anomaly_service's own
    # `IncidentResponse.dataset_id`) -- surfaced here verbatim so the
    # frontend never has to guess or silently assume an Investigation
    # belongs to whichever dataset happens to be selected right now.
    datasetId: str
    # AD-12 follow-up: the Incident's own `last_analysis_version_id` --
    # which DatasetVersion's analysis run most recently touched this
    # incident (anomalies re-detected, correlation re-run). This is a
    # "last touched by" pointer, not a creation-time fact (the Incident
    # row is continuously reconciled by fingerprint within its dataset,
    # by design -- see docs/DECISIONS.md AD-12) -- surfaced so the
    # frontend can tell which version's analysis this investigation's
    # incident-level state currently reflects.
    datasetVersionId: str
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


class RootCauseActionResponse(BaseModel):
    """
    Response for the root-cause lifecycle actions (confirm/reject/refresh)
    -- root_cause_service's real capability, previously implemented but
    unreachable through the Gateway. Deliberately a narrower DTO than
    `InvestigationResponse`: these actions mutate only the RootCause
    sub-resource, so the response reflects that resource alone. The
    frontend refetches the full Investigation afterward to pick up any
    downstream effects rather than this endpoint trying to represent them.
    """

    incidentId: str
    status: RootCauseLifecycleStatus
    headline: str
    reasoning: str
    confidenceLevel: ConfidenceLevel
