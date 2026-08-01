import dataclasses

import pytest

from backend.services.recommendation_service.app.domain.evidence_source import EvidenceSource
from backend.services.recommendation_service.app.domain.recommendation import Recommendation
from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.supporting_evidence import SupportingEvidence

_VALID_EVIDENCE = (SupportingEvidence(source=EvidenceSource.INCIDENT, description="evidence", weight=10),)


def _build(**overrides) -> Recommendation:
    fields = dict(
        incident_id="INC-1",
        category=RecommendationCategory.MONITOR,
        action="Continue monitoring.",
        priority=RecommendationPriority.LOW,
        score=30,
        rationale="Low signal.",
        priority_rationale="Low urgency.",
        supporting_evidence=_VALID_EVIDENCE,
    )
    fields.update(overrides)
    return Recommendation(**fields)


def test_builds_a_valid_recommendation():
    recommendation = _build()

    assert recommendation.category == RecommendationCategory.MONITOR
    assert recommendation.priority == RecommendationPriority.LOW
    assert recommendation.score == 30


def test_is_immutable():
    recommendation = _build()
    with pytest.raises(dataclasses.FrozenInstanceError):
        recommendation.score = 99


def test_rejects_missing_incident_id():
    with pytest.raises(ValueError, match="incident_id"):
        _build(incident_id="")


def test_rejects_missing_action():
    with pytest.raises(ValueError, match="Recommended Action"):
        _build(action="")


@pytest.mark.parametrize("score", [-1, 101, -100, 1000])
def test_rejects_out_of_range_score(score):
    with pytest.raises(ValueError, match="score"):
        _build(score=score)


@pytest.mark.parametrize("score", [0, 50, 100])
def test_accepts_boundary_scores(score):
    recommendation = _build(score=score)
    assert recommendation.score == score


def test_rejects_missing_rationale():
    with pytest.raises(ValueError, match="Recommendation Rationale"):
        _build(rationale="")


def test_rejects_missing_priority_rationale():
    with pytest.raises(ValueError, match="Priority Rationale"):
        _build(priority_rationale="")


def test_rejects_empty_supporting_evidence():
    with pytest.raises(ValueError, match="Supporting Evidence"):
        _build(supporting_evidence=())


def test_supporting_evidence_is_a_tuple_of_structured_objects():
    recommendation = _build()
    assert all(isinstance(evidence, SupportingEvidence) for evidence in recommendation.supporting_evidence)
