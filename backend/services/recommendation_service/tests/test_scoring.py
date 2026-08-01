import pytest

from backend.services.recommendation_service.app.domain import scoring
from backend.services.recommendation_service.app.domain.evidence_source import EvidenceSource
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.supporting_evidence import SupportingEvidence


def _evidence(weight: int) -> SupportingEvidence:
    return SupportingEvidence(source=EvidenceSource.INCIDENT, description="evidence", weight=weight)


@pytest.mark.parametrize(
    "priority,expected_base",
    [
        (RecommendationPriority.CRITICAL, 70),
        (RecommendationPriority.HIGH, 55),
        (RecommendationPriority.MEDIUM, 40),
        (RecommendationPriority.LOW, 25),
    ],
)
def test_score_equals_priority_base_with_no_evidence(priority, expected_base):
    assert scoring.compute_score(priority, ()) == expected_base


def test_score_adds_evidence_weights():
    score = scoring.compute_score(RecommendationPriority.MEDIUM, (_evidence(10), _evidence(5)))
    assert score == 40 + 10 + 5


def test_score_is_clamped_to_the_maximum():
    score = scoring.compute_score(RecommendationPriority.CRITICAL, (_evidence(100), _evidence(100)))
    assert score == scoring.MAX_SCORE


def test_score_is_clamped_to_the_minimum_with_negative_evidence():
    score = scoring.compute_score(RecommendationPriority.LOW, (_evidence(-1000),))
    assert score == scoring.MIN_SCORE


def test_score_is_always_within_bounds():
    for priority in RecommendationPriority:
        for weight in (-500, -1, 0, 1, 500):
            score = scoring.compute_score(priority, (_evidence(weight),))
            assert scoring.MIN_SCORE <= score <= scoring.MAX_SCORE


def test_is_deterministic():
    evidence = (_evidence(10), _evidence(20))
    first = scoring.compute_score(RecommendationPriority.HIGH, evidence)
    second = scoring.compute_score(RecommendationPriority.HIGH, evidence)
    assert first == second


def test_every_priority_has_a_distinct_base_score():
    bases = [scoring.BASE_SCORE_BY_PRIORITY[priority] for priority in RecommendationPriority]
    assert len(bases) == len(set(bases))


def test_base_scores_are_ordered_by_urgency():
    by_priority = scoring.BASE_SCORE_BY_PRIORITY
    assert (
        by_priority[RecommendationPriority.CRITICAL]
        > by_priority[RecommendationPriority.HIGH]
        > by_priority[RecommendationPriority.MEDIUM]
        > by_priority[RecommendationPriority.LOW]
    )
