import uuid

from backend.services.business_impact_service.app.domain.business_impact_assessment import BusinessImpactAssessment
from backend.services.business_impact_service.app.domain.business_priority import BusinessPriority
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.mappers.output_mapper import BusinessImpactOutputMapper
from backend.shared.constants.enums.root_cause import RootCause


def _assessment(**overrides) -> BusinessImpactAssessment:
    defaults = dict(
        incident_id="INC-0001",
        root_cause=RootCause.SERVICE_OUTAGE,
        overall_severity=ImpactLevel.HIGH,
        business_priority=BusinessPriority.HIGH,
        business_score=78,
        confidence=80,
        financial_impact=ImpactLevel.HIGH,
        customer_impact=ImpactLevel.MEDIUM,
        operational_impact=ImpactLevel.CRITICAL,
        sla_impact=ImpactLevel.LOW,
        reputation_impact=ImpactLevel.NONE,
        estimated_affected_customers=250,
        explanation="Overall business impact is high.",
    )
    defaults.update(overrides)
    return BusinessImpactAssessment(**defaults)


def test_to_orm_copies_every_field_verbatim():
    incident_id = uuid.uuid4()
    root_cause_id = uuid.uuid4()
    assessment = _assessment()

    entity = BusinessImpactOutputMapper.to_orm(incident_id, root_cause_id, assessment)

    assert entity.incident_id == incident_id
    assert entity.root_cause_id == root_cause_id
    assert entity.financial == ImpactLevel.HIGH
    assert entity.customer == ImpactLevel.MEDIUM
    assert entity.operational == ImpactLevel.CRITICAL
    assert entity.sla == ImpactLevel.LOW
    assert entity.reputation == ImpactLevel.NONE
    assert entity.overall_score == 78
    assert entity.overall_severity == ImpactLevel.HIGH
    assert entity.business_priority == BusinessPriority.HIGH
    assert entity.confidence == 80
    assert entity.estimated_affected_customers == 250
    assert entity.explanation == "Overall business impact is high."


def test_to_orm_uses_the_supplied_identifiers_not_the_assessment_string_id():
    # BusinessImpactAssessment.incident_id is a string (Phase 7 Step 1
    # domain model); the ORM entity's incident_id/root_cause_id columns are
    # always populated from the explicit UUID parameters, never parsed back
    # out of the assessment.
    incident_id = uuid.uuid4()
    root_cause_id = uuid.uuid4()
    assessment = _assessment(incident_id="not-a-uuid-at-all")

    entity = BusinessImpactOutputMapper.to_orm(incident_id, root_cause_id, assessment)

    assert entity.incident_id == incident_id
    assert entity.root_cause_id == root_cause_id
