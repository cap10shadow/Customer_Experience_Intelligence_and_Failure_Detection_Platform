from dataclasses import dataclass


@dataclass(frozen=True)
class BusinessImpactSummary:
    """
    Plain, persistence-independent view of a Phase 7 Business Impact result,
    as seen by the Recommendation Engine.

    Deliberately NOT the Business Impact Service's own `BusinessImpactAssessment`,
    `ImpactLevel`, or `BusinessPriority` types: this engine must never import
    across a service boundary (DATA-002). `overall_severity`, `business_priority`,
    and the five per-dimension impact fields are plain `str` rather than local
    re-declarations of those enums -- the same choice Evaluation Service's own
    `CompletedIntelligence` made for the identical reason: those are Business
    Impact Service's own domain-local types, not shared enums, and must not be
    imported or shadowed here. A later step is responsible for constructing
    this from a real BusinessImpactAssessment record.
    """

    business_score: int
    overall_severity: str
    business_priority: str
    confidence: int
    financial_impact: str
    customer_impact: str
    operational_impact: str
    sla_impact: str
    reputation_impact: str
