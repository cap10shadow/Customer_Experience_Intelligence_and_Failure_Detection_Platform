"""
Phase 12 Batch 2 -- typed input/output contracts for the 7 read-only tool
adapters (docs/architecture/phase-12/PHASE_12_ARCHITECTURE.md §13 Tool
Contract Matrix). Reuses the existing `EvidenceReference`/`RelatedEntity`
shapes from `schemas/copilot.py` (§14.1) rather than defining a second,
competing evidence model. Enum-valued domain fields (category, severity,
status, etc.) are typed as plain `str`, matching every existing
cross-service DTO convention in this repository (DATA-002: a service
never imports another service's domain enum class).
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from backend.services.copilot_service.app.schemas.copilot import EvidenceReference

# ---------------------------------------------------------------------------
# 13.1 / 13.2 -- Recommendation Tool, Recommendation Decision Status Tool
# ---------------------------------------------------------------------------


class RecommendationToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation_id: Optional[str] = None
    incident_id: Optional[str] = None
    limit: int = 20
    include_statistics: bool = False


class RecommendationDetail(BaseModel):
    recommendation_id: str
    incident_id: str
    generation_id: str
    category: str
    priority: str
    score: int
    action: str
    created_at: str
    recommendation_rationale: Optional[str] = None
    priority_rationale: Optional[str] = None


class RecommendationStatistics(BaseModel):
    total_count: int
    category_counts: Dict[str, int]
    priority_counts: Dict[str, int]
    average_score: float


class RecommendationToolResult(BaseModel):
    found: bool
    error: Optional[str] = None
    recommendations: List[RecommendationDetail] = []
    statistics: Optional[RecommendationStatistics] = None
    evidence_references: List[EvidenceReference] = []


class RecommendationDecisionStatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation_id: str


class RecommendationDecisionStatusResult(BaseModel):
    found: bool
    error: Optional[str] = None
    recommendation_id: Optional[str] = None
    decision: Optional[str] = None
    decision_note: Optional[str] = None
    decided_at: Optional[str] = None
    evidence_references: List[EvidenceReference] = []


# ---------------------------------------------------------------------------
# 13.3 -- Root Cause Tool
# ---------------------------------------------------------------------------


class RootCauseToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: Optional[str] = None
    root_cause_id: Optional[str] = None


class RootCauseEvidenceItem(BaseModel):
    type: str
    description: str
    weight: int


class RootCauseDetail(BaseModel):
    root_cause_id: str
    incident_id: str
    cause: str
    confidence_score: int
    confidence_level: str
    explanation: str
    rule_version: str
    status: str
    created_at: str
    updated_at: str
    evidence: List[RootCauseEvidenceItem] = []


class RootCauseToolResult(BaseModel):
    found: bool
    error: Optional[str] = None
    root_cause: Optional[RootCauseDetail] = None
    evidence_references: List[EvidenceReference] = []


# ---------------------------------------------------------------------------
# 13.4 -- Business Impact Tool
# ---------------------------------------------------------------------------


class BusinessImpactToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: Optional[str] = None
    assessment_id: Optional[str] = None


class BusinessImpactDetail(BaseModel):
    assessment_id: str
    incident_id: str
    root_cause_id: str
    financial: str
    customer: str
    operational: str
    sla: str
    reputation: str
    overall_score: int
    overall_severity: str
    business_priority: str
    confidence: int
    estimated_affected_customers: int
    explanation: str
    status: str
    created_at: str
    updated_at: str


class BusinessImpactToolResult(BaseModel):
    found: bool
    error: Optional[str] = None
    assessment: Optional[BusinessImpactDetail] = None
    evidence_references: List[EvidenceReference] = []


# ---------------------------------------------------------------------------
# 13.5 -- Investigation Tool (Copilot-owned composition, §8)
# ---------------------------------------------------------------------------


class InvestigationToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: str


class InvestigationIncident(BaseModel):
    incident_id: str
    incident_key: str
    title: str
    severity: str
    status: str
    confidence_score: int
    summary: str
    started_at: str
    last_updated_at: str
    resolved_at: Optional[str] = None


class InvestigationAnomaly(BaseModel):
    anomaly_id: str
    type: str
    severity: str
    entity_type: str
    entity_value: Optional[str] = None
    explanation: str
    triggered_rule: str
    first_detected_at: str
    last_seen_at: str


class InvestigationNlpSummary(BaseModel):
    issue_category: str
    total_count: int
    sentiment_counts: Dict[str, int]


class InvestigationToolResult(BaseModel):
    """
    `found=False` only when the incident itself is missing/unreachable
    (essential). Every other source is degrade-gracefully: a failed or
    absent source is represented by an explicit `limitations` entry, the
    corresponding field stays empty/None, and every other successfully
    retrieved source is still returned (§13.5/§22 -- never block the
    whole answer on one failed source).
    """

    found: bool
    error: Optional[str] = None
    incident: Optional[InvestigationIncident] = None
    anomalies: List[InvestigationAnomaly] = []
    root_cause: Optional[RootCauseDetail] = None
    business_impact: Optional[BusinessImpactDetail] = None
    latest_recommendations: List[RecommendationDetail] = []
    nlp_summary: Optional[InvestigationNlpSummary] = None
    limitations: List[str] = []
    evidence_references: List[EvidenceReference] = []


# ---------------------------------------------------------------------------
# 13.6 -- Analytics / Trend Tool
# ---------------------------------------------------------------------------

TrendDimension = str  # "summary" | "daily" | "categories" | "regions" | "sentiment" | "urgency"


class AnalyticsToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: TrendDimension = "summary"
    days: int = 30


class VolumeTrendPoint(BaseModel):
    date: str
    count: int


class CategoryTrendPoint(BaseModel):
    category: str
    count: int


class RegionTrendPoint(BaseModel):
    region: str
    count: int


class SentimentTrendPoint(BaseModel):
    date: str
    average_score: float
    label_counts: Dict[str, int]


class UrgencyTrendPoint(BaseModel):
    urgency: str
    count: int


class AnalyticsToolResult(BaseModel):
    found: bool
    error: Optional[str] = None
    period: Optional[str] = None
    volume: List[VolumeTrendPoint] = []
    categories: List[CategoryTrendPoint] = []
    regions: List[RegionTrendPoint] = []
    sentiment: List[SentimentTrendPoint] = []
    urgency: List[UrgencyTrendPoint] = []
    # §15/§18: anomaly_service's trend DTOs carry no computation
    # timestamp -- verified directly against
    # anomaly_service/app/schemas/trends.py. Never fabricated from
    # request time; always this fixed, honest statement instead.
    freshness_note: str = "The source does not provide a computation timestamp for trend data."
    evidence_references: List[EvidenceReference] = []


# ---------------------------------------------------------------------------
# 13.7 -- Administration / Configuration Read Tool
# ---------------------------------------------------------------------------


class AdministrationToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    include_health: bool = True
    include_configuration: bool = True


class ServiceHealthStatus(BaseModel):
    service: str
    status: str
    detail: str


class DimensionWeight(BaseModel):
    dimension: str
    weight: float


class ImpactLevelPoints(BaseModel):
    level: str
    points: int


class SeverityBand(BaseModel):
    upper_bound_inclusive: int
    level: str


class AdministrationToolResult(BaseModel):
    error: Optional[str] = None
    service_health: List[ServiceHealthStatus] = []
    dimension_weights: List[DimensionWeight] = []
    impact_level_points: List[ImpactLevelPoints] = []
    severity_bands: List[SeverityBand] = []
    evidence_references: List[EvidenceReference] = []
