import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field

from backend.services.business_impact_service.app.domain.business_priority import BusinessPriority
from backend.services.business_impact_service.app.domain.confidence import classify_confidence
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.shared.constants.enums.business_impact_assessment import BusinessImpactAssessmentStatus


class CreateBusinessImpactRequest(BaseModel):
    """
    Request body for POST /business-impact: which Incident to analyze, and
    which Dataset that Incident belongs to. `dataset_id` must be supplied
    by the caller (the Gateway's orchestrator) -- the Business Impact
    Service has no independent way to look it up.
    """
    incident_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_version_id: uuid.UUID


class BusinessImpactAssessmentResponse(BaseModel):
    """Full explainable snapshot of a persisted BusinessImpactAssessment."""

    assessment_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_version_id: uuid.UUID
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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def confidence_level(self) -> str:
        """
        Business-Impact-owned classification of `confidence` (Step 7.X
        A-05) -- computed fresh at response-serialization time from the
        engine's own, unmodified `confidence` value, never persisted and
        never touching the frozen Business Impact Engine or its ORM
        entity (BusinessImpactAssessmentEntity's own docstring: "no
        additional calculation happens at the persistence layer"). See
        domain/confidence.py for the ARB-008 rationale and threshold
        justification.
        """
        return classify_confidence(self.confidence)
