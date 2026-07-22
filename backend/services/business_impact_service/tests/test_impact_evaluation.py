import pytest

from backend.services.business_impact_service.app.domain.impact_dimension import ImpactDimension
from backend.services.business_impact_service.app.domain.impact_evaluation import ImpactEvaluation
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel


def test_constructs_with_required_fields_only():
    evaluation = ImpactEvaluation(
        impact_dimension=ImpactDimension.FINANCIAL,
        impact_level=ImpactLevel.HIGH,
        reason="High-severity incident",
    )
    assert evaluation.impact_dimension == ImpactDimension.FINANCIAL
    assert evaluation.impact_level == ImpactLevel.HIGH
    assert evaluation.reason == "High-severity incident"
    assert evaluation.metadata is None


def test_constructs_with_optional_metadata():
    evaluation = ImpactEvaluation(
        impact_dimension=ImpactDimension.CUSTOMER,
        impact_level=ImpactLevel.MEDIUM,
        reason="120 customers affected",
        metadata={"affected_customer_count": 120},
    )
    assert evaluation.metadata == {"affected_customer_count": 120}


def test_is_immutable():
    evaluation = ImpactEvaluation(
        impact_dimension=ImpactDimension.SLA,
        impact_level=ImpactLevel.LOW,
        reason="1 SLA breach recorded",
    )
    with pytest.raises(AttributeError):
        evaluation.impact_level = ImpactLevel.CRITICAL


def test_equality_is_value_based():
    first = ImpactEvaluation(impact_dimension=ImpactDimension.REPUTATION, impact_level=ImpactLevel.NONE, reason="x")
    second = ImpactEvaluation(impact_dimension=ImpactDimension.REPUTATION, impact_level=ImpactLevel.NONE, reason="x")
    assert first == second
