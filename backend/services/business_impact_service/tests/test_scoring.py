import pytest

from backend.services.business_impact_service.app.domain.business_impact_profile import BusinessImpactProfile
from backend.services.business_impact_service.app.domain.business_priority import BusinessPriority
from backend.services.business_impact_service.app.domain.impact_dimension import ImpactDimension
from backend.services.business_impact_service.app.domain.impact_evaluation import ImpactEvaluation
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.services.scoring import (
    classify_business_priority,
    classify_severity,
    compute_confidence,
    escalate_level,
)


@pytest.mark.parametrize(
    "score,expected",
    [
        (0, ImpactLevel.NONE),
        (20, ImpactLevel.NONE),
        (21, ImpactLevel.LOW),
        (40, ImpactLevel.LOW),
        (41, ImpactLevel.MEDIUM),
        (60, ImpactLevel.MEDIUM),
        (61, ImpactLevel.HIGH),
        (80, ImpactLevel.HIGH),
        (81, ImpactLevel.CRITICAL),
        (100, ImpactLevel.CRITICAL),
    ],
)
def test_classify_severity_bands(score, expected):
    assert classify_severity(score) == expected


@pytest.mark.parametrize(
    "severity,expected",
    [
        (ImpactLevel.NONE, BusinessPriority.LOW),
        (ImpactLevel.LOW, BusinessPriority.LOW),
        (ImpactLevel.MEDIUM, BusinessPriority.MEDIUM),
        (ImpactLevel.HIGH, BusinessPriority.HIGH),
        (ImpactLevel.CRITICAL, BusinessPriority.CRITICAL),
    ],
)
def test_classify_business_priority(severity, expected):
    assert classify_business_priority(severity) == expected


@pytest.mark.parametrize(
    "level,expected",
    [
        (ImpactLevel.NONE, ImpactLevel.LOW),
        (ImpactLevel.LOW, ImpactLevel.MEDIUM),
        (ImpactLevel.MEDIUM, ImpactLevel.HIGH),
        (ImpactLevel.HIGH, ImpactLevel.CRITICAL),
        (ImpactLevel.CRITICAL, ImpactLevel.CRITICAL),
    ],
)
def test_escalate_level(level, expected):
    assert escalate_level(level) == expected


def _profile_with_levels(levels):
    dimensions = [
        ImpactDimension.FINANCIAL,
        ImpactDimension.CUSTOMER,
        ImpactDimension.OPERATIONAL,
        ImpactDimension.SLA,
        ImpactDimension.REPUTATION,
    ]
    evaluations = {
        dim.value: ImpactEvaluation(impact_dimension=dim, impact_level=level, reason="x")
        for dim, level in zip(dimensions, levels)
    }
    return BusinessImpactProfile(
        financial=evaluations["financial"],
        customer=evaluations["customer"],
        operational=evaluations["operational"],
        sla=evaluations["sla"],
        reputation=evaluations["reputation"],
    )


def test_compute_confidence_is_zero_when_all_dimensions_are_none():
    profile = _profile_with_levels([ImpactLevel.NONE] * 5)
    assert compute_confidence(profile) == 0


def test_compute_confidence_is_100_when_all_dimensions_carry_signal():
    profile = _profile_with_levels([ImpactLevel.LOW] * 5)
    assert compute_confidence(profile) == 100


def test_compute_confidence_reflects_partial_completeness():
    profile = _profile_with_levels(
        [ImpactLevel.HIGH, ImpactLevel.NONE, ImpactLevel.MEDIUM, ImpactLevel.NONE, ImpactLevel.NONE]
    )
    assert compute_confidence(profile) == 40  # 2 of 5 informative
