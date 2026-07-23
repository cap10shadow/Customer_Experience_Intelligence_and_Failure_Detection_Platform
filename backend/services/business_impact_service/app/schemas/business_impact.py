import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.services.business_impact_service.app.domain.business_priority import BusinessPriority
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.shared.constants.enums.business_impact_assessment import BusinessImpactAssessmentStatus


class CreateBusinessImpactRequest(BaseModel):
    """Request body for POST /business-impact: which Incident to analyze."""
    incident_id: uuid.UUID


class BusinessImpactAssessmentResponse(BaseModel):
    """Full explainable snapshot of a persisted BusinessImpactAssessment."""

    assessment_id: uuid.UUID
    incident_id: uuid.UUID
    root_cause_id: uuid.UUID
    financial: ImpactLevel
    customer: ImpactLevel
    operational: ImpactLevel
    sla: ImpactLevel
    reputation: ImpactLevel
    overall_score: int
    overall_severity: ImpactLevel
    business_priority: BusinessPriority
    confidence: int
    estimated_affected_customers: int
    explanation: str
    status: BusinessImpactAssessmentStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
