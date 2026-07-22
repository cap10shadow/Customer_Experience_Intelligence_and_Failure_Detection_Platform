import pytest

from backend.services.business_impact_service.app.domain.business_impact_profile import BusinessImpactProfile
from backend.services.business_impact_service.app.domain.impact_dimension import ImpactDimension
from backend.services.business_impact_service.app.domain.impact_evaluation import ImpactEvaluation
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel


def _evaluation(dimension: ImpactDimension, level: ImpactLevel = ImpactLevel.NONE) -> ImpactEvaluation:
    return ImpactEvaluation(impact_dimension=dimension, impact_level=level, reason=f"{dimension.value} reason")


def test_all_evaluations_returns_the_five_dimensions_in_canonical_order():
    profile = BusinessImpactProfile(
        financial=_evaluation(ImpactDimension.FINANCIAL, ImpactLevel.HIGH),
        customer=_evaluation(ImpactDimension.CUSTOMER, ImpactLevel.MEDIUM),
        operational=_evaluation(ImpactDimension.OPERATIONAL, ImpactLevel.LOW),
        sla=_evaluation(ImpactDimension.SLA, ImpactLevel.NONE),
        reputation=_evaluation(ImpactDimension.REPUTATION, ImpactLevel.CRITICAL),
    )

    evaluations = profile.all_evaluations()

    assert len(evaluations) == 5
    assert [e.impact_dimension for e in evaluations] == [
        ImpactDimension.FINANCIAL,
        ImpactDimension.CUSTOMER,
        ImpactDimension.OPERATIONAL,
        ImpactDimension.SLA,
        ImpactDimension.REPUTATION,
    ]


def test_is_immutable():
    profile = BusinessImpactProfile(
        financial=_evaluation(ImpactDimension.FINANCIAL),
        customer=_evaluation(ImpactDimension.CUSTOMER),
        operational=_evaluation(ImpactDimension.OPERATIONAL),
        sla=_evaluation(ImpactDimension.SLA),
        reputation=_evaluation(ImpactDimension.REPUTATION),
    )
    with pytest.raises(AttributeError):
        profile.financial = _evaluation(ImpactDimension.FINANCIAL, ImpactLevel.CRITICAL)
