from backend.services.business_impact_service.app.domain.business_impact_profile import BusinessImpactProfile
from backend.services.business_impact_service.app.domain.impact_dimension import ImpactDimension
from backend.services.business_impact_service.app.domain.impact_evaluation import ImpactEvaluation
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.services.weighting import (
    DIMENSION_WEIGHTS,
    cap_score,
    compute_business_score,
)


def _evaluation(dimension: ImpactDimension, level: ImpactLevel) -> ImpactEvaluation:
    return ImpactEvaluation(impact_dimension=dimension, impact_level=level, reason="x")


def test_weights_are_centralized_and_sum_to_one():
    assert set(DIMENSION_WEIGHTS.keys()) == {
        ImpactDimension.FINANCIAL,
        ImpactDimension.CUSTOMER,
        ImpactDimension.OPERATIONAL,
        ImpactDimension.SLA,
        ImpactDimension.REPUTATION,
    }
    assert DIMENSION_WEIGHTS[ImpactDimension.FINANCIAL] == 0.35
    assert DIMENSION_WEIGHTS[ImpactDimension.CUSTOMER] == 0.25
    assert DIMENSION_WEIGHTS[ImpactDimension.OPERATIONAL] == 0.15
    assert DIMENSION_WEIGHTS[ImpactDimension.SLA] == 0.15
    assert DIMENSION_WEIGHTS[ImpactDimension.REPUTATION] == 0.10
    assert sum(DIMENSION_WEIGHTS.values()) == 1.0


def test_business_score_is_zero_when_every_dimension_is_none():
    profile = BusinessImpactProfile(
        financial=_evaluation(ImpactDimension.FINANCIAL, ImpactLevel.NONE),
        customer=_evaluation(ImpactDimension.CUSTOMER, ImpactLevel.NONE),
        operational=_evaluation(ImpactDimension.OPERATIONAL, ImpactLevel.NONE),
        sla=_evaluation(ImpactDimension.SLA, ImpactLevel.NONE),
        reputation=_evaluation(ImpactDimension.REPUTATION, ImpactLevel.NONE),
    )
    assert compute_business_score(profile) == 0


def test_business_score_is_100_when_every_dimension_is_critical():
    profile = BusinessImpactProfile(
        financial=_evaluation(ImpactDimension.FINANCIAL, ImpactLevel.CRITICAL),
        customer=_evaluation(ImpactDimension.CUSTOMER, ImpactLevel.CRITICAL),
        operational=_evaluation(ImpactDimension.OPERATIONAL, ImpactLevel.CRITICAL),
        sla=_evaluation(ImpactDimension.SLA, ImpactLevel.CRITICAL),
        reputation=_evaluation(ImpactDimension.REPUTATION, ImpactLevel.CRITICAL),
    )
    assert compute_business_score(profile) == 100


def test_business_score_weights_financial_highest():
    # Financial CRITICAL (100 pts * 0.35 = 35) with everything else NONE
    # must outscore Reputation CRITICAL (100 pts * 0.10 = 10) alone.
    financial_heavy = BusinessImpactProfile(
        financial=_evaluation(ImpactDimension.FINANCIAL, ImpactLevel.CRITICAL),
        customer=_evaluation(ImpactDimension.CUSTOMER, ImpactLevel.NONE),
        operational=_evaluation(ImpactDimension.OPERATIONAL, ImpactLevel.NONE),
        sla=_evaluation(ImpactDimension.SLA, ImpactLevel.NONE),
        reputation=_evaluation(ImpactDimension.REPUTATION, ImpactLevel.NONE),
    )
    reputation_heavy = BusinessImpactProfile(
        financial=_evaluation(ImpactDimension.FINANCIAL, ImpactLevel.NONE),
        customer=_evaluation(ImpactDimension.CUSTOMER, ImpactLevel.NONE),
        operational=_evaluation(ImpactDimension.OPERATIONAL, ImpactLevel.NONE),
        sla=_evaluation(ImpactDimension.SLA, ImpactLevel.NONE),
        reputation=_evaluation(ImpactDimension.REPUTATION, ImpactLevel.CRITICAL),
    )
    assert compute_business_score(financial_heavy) == 35
    assert compute_business_score(reputation_heavy) == 10
    assert compute_business_score(financial_heavy) > compute_business_score(reputation_heavy)


def test_cap_score_clamps_to_valid_range():
    assert cap_score(-10) == 0
    assert cap_score(150) == 100
    assert cap_score(55) == 55
