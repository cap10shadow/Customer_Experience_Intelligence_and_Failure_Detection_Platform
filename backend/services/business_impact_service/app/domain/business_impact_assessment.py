from dataclasses import dataclass

from backend.services.business_impact_service.app.domain.business_priority import BusinessPriority
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.shared.constants.enums.root_cause import RootCause


@dataclass(frozen=True)
class BusinessImpactAssessment:
    """
    Final, immutable Business Impact Analysis result for one Incident.

    Pure in-memory value object -- no ORM fields, no timestamps, no
    persistence metadata (out of scope for Phase 7 Step 1).
    """

    incident_id: str
    root_cause: RootCause
    overall_severity: ImpactLevel
    business_priority: BusinessPriority
    business_score: int
    confidence: int
    financial_impact: ImpactLevel
    customer_impact: ImpactLevel
    operational_impact: ImpactLevel
    sla_impact: ImpactLevel
    reputation_impact: ImpactLevel
    estimated_affected_customers: int
    explanation: str
