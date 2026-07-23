import uuid

from backend.services.business_impact_service.app.domain.business_impact_assessment import BusinessImpactAssessment
from backend.services.business_impact_service.app.models.business_impact_assessment import (
    BusinessImpactAssessmentEntity,
)


class BusinessImpactOutputMapper:
    """
    Business Impact Output Mapper

    Operational Purpose:
    Translates a `BusinessImpactAssessment` (the frozen Engine's in-memory
    output) into a persistable `BusinessImpactAssessmentEntity`. The Engine
    must never return or construct ORM objects -- this mapper is the only
    place that boundary is crossed, in the opposite direction from
    `BusinessImpactInputMapper`.

    Every field here is copied verbatim from the assessment; `incident_id`
    and `root_cause_id` are supplied explicitly since the domain assessment
    itself carries only `incident_id` as a string (not the original UUID)
    and no `root_cause_id` at all -- the same explicit-parameter pattern
    Root Cause Service's own `RootCauseMapper.to_orm` uses.
    """

    @staticmethod
    def to_orm(
        incident_id: uuid.UUID,
        root_cause_id: uuid.UUID,
        assessment: BusinessImpactAssessment,
    ) -> BusinessImpactAssessmentEntity:
        """Builds a brand-new BusinessImpactAssessmentEntity row for a freshly-computed assessment."""
        return BusinessImpactAssessmentEntity(
            incident_id=incident_id,
            root_cause_id=root_cause_id,
            financial=assessment.financial_impact,
            customer=assessment.customer_impact,
            operational=assessment.operational_impact,
            sla=assessment.sla_impact,
            reputation=assessment.reputation_impact,
            overall_score=assessment.business_score,
            overall_severity=assessment.overall_severity,
            business_priority=assessment.business_priority,
            confidence=assessment.confidence,
            estimated_affected_customers=assessment.estimated_affected_customers,
            explanation=assessment.explanation,
        )
