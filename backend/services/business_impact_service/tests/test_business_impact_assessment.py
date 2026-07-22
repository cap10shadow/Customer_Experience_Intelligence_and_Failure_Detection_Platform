import pytest

from backend.services.business_impact_service.app.domain.business_impact_assessment import BusinessImpactAssessment
from backend.services.business_impact_service.app.domain.business_priority import BusinessPriority
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.shared.constants.enums.root_cause import RootCause


def _assessment(**overrides) -> BusinessImpactAssessment:
    defaults = dict(
        incident_id="INC-TEST0001",
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


def test_constructs_with_all_fields():
    assessment = _assessment()
    assert assessment.incident_id == "INC-TEST0001"
    assert assessment.root_cause == RootCause.SERVICE_OUTAGE
    assert assessment.overall_severity == ImpactLevel.HIGH
    assert assessment.business_priority == BusinessPriority.HIGH
    assert assessment.business_score == 78
    assert assessment.confidence == 80
    assert assessment.estimated_affected_customers == 250


def test_is_immutable():
    assessment = _assessment()
    with pytest.raises(AttributeError):
        assessment.business_score = 100


def test_has_no_orm_or_persistence_fields():
    field_names = set(_assessment().__dataclass_fields__.keys())
    forbidden = {"id", "created_at", "updated_at", "version"}
    assert not (field_names & forbidden)
