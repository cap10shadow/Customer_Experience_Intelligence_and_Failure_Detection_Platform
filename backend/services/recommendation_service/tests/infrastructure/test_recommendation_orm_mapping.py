"""
ORM mapping tests: pure Python round-trip verification of
RecommendationModelMapper's to_orm()/to_domain() translation -- no
database required. Repository-level tests that actually exercise SQL
execution live in test_postgresql_recommendation_repository.py.
"""

import uuid
from datetime import datetime, timezone

from backend.services.recommendation_service.app.domain.evidence_source import EvidenceSource
from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.supporting_evidence import SupportingEvidence
from backend.services.recommendation_service.app.infrastructure.persistence.models.recommendation_model import (
    RecommendationModel,
)
from backend.services.recommendation_service.app.infrastructure.persistence.repositories.recommendation_model_mapper import (
    RecommendationModelMapper,
)


def _simulate_flush(model: RecommendationModel) -> None:
    """Mimics what a real PostgreSQL flush would populate (recommendation_id default, created_at server_default)."""
    model.recommendation_id = uuid.uuid4()
    model.created_at = datetime.now(timezone.utc)


def test_to_orm_maps_every_relational_field(make_recommendation):
    recommendation = make_recommendation(category=RecommendationCategory.ESCALATE, priority=RecommendationPriority.CRITICAL, score=90)
    generation_id = uuid.uuid4()

    model = RecommendationModelMapper.to_orm(recommendation, generation_id=generation_id)

    assert isinstance(model, RecommendationModel)
    assert model.incident_id == recommendation.incident_id
    assert model.generation_id == generation_id
    assert model.category == RecommendationCategory.ESCALATE
    assert model.priority == RecommendationPriority.CRITICAL
    assert model.score == 90
    assert model.action == recommendation.action


def test_to_orm_serializes_rationale_and_priority_rationale_as_plain_jsonb_strings(make_recommendation):
    recommendation = make_recommendation(rationale="Reason A.", priority_rationale="Priority reason A.")

    model = RecommendationModelMapper.to_orm(recommendation, generation_id=uuid.uuid4())

    assert model.recommendation_rationale == "Reason A."
    assert model.priority_rationale == "Priority reason A."


def test_to_orm_serializes_supporting_evidence_as_jsonb_list(make_recommendation):
    evidence = (
        SupportingEvidence(source=EvidenceSource.INCIDENT, description="signal one", weight=10),
        SupportingEvidence(source=EvidenceSource.ROOT_CAUSE, description="signal two", weight=15),
    )
    recommendation = make_recommendation(supporting_evidence=evidence)

    model = RecommendationModelMapper.to_orm(recommendation, generation_id=uuid.uuid4())

    assert model.supporting_evidence == [
        {"source": "incident", "description": "signal one", "weight": 10},
        {"source": "root_cause", "description": "signal two", "weight": 15},
    ]


def test_round_trip_to_orm_then_to_domain_preserves_every_field(make_recommendation):
    evidence = (SupportingEvidence(source=EvidenceSource.NLP_INTELLIGENCE, description="negative sentiment", weight=12),)
    recommendation = make_recommendation(
        incident_id="INC-ROUNDTRIP",
        category=RecommendationCategory.CUSTOMER_COMMUNICATION,
        action="Issue proactive customer communication.",
        priority=RecommendationPriority.HIGH,
        score=72,
        rationale="Customer sentiment has deteriorated.",
        priority_rationale="Highly negative sentiment warrants high urgency.",
        supporting_evidence=evidence,
    )
    generation_id = uuid.uuid4()

    model = RecommendationModelMapper.to_orm(recommendation, generation_id=generation_id)
    _simulate_flush(model)

    record = RecommendationModelMapper.to_domain(model)

    assert record.recommendation_id == model.recommendation_id
    assert record.generation_id == generation_id
    assert record.created_at == model.created_at
    assert record.recommendation == recommendation


def test_round_trip_preserves_category_and_priority_enum_types(make_recommendation):
    recommendation = make_recommendation()
    model = RecommendationModelMapper.to_orm(recommendation, generation_id=uuid.uuid4())
    _simulate_flush(model)

    record = RecommendationModelMapper.to_domain(model)

    assert isinstance(record.recommendation.category, RecommendationCategory)
    assert isinstance(record.recommendation.priority, RecommendationPriority)


def test_round_trip_preserves_evidence_source_enum_type(make_recommendation):
    evidence = (SupportingEvidence(source=EvidenceSource.ANOMALY_INTELLIGENCE, description="sla breach", weight=15),)
    recommendation = make_recommendation(supporting_evidence=evidence)
    model = RecommendationModelMapper.to_orm(recommendation, generation_id=uuid.uuid4())
    _simulate_flush(model)

    record = RecommendationModelMapper.to_domain(model)

    assert isinstance(record.recommendation.supporting_evidence[0].source, EvidenceSource)
    assert record.recommendation.supporting_evidence[0].source == EvidenceSource.ANOMALY_INTELLIGENCE


def test_to_domain_defaults_decision_fields_to_none_for_a_never_decided_row(make_recommendation):
    """A freshly-mapped ORM row (decision/decision_note/decided_at all unset, i.e. NULL) maps to None -- never a fabricated PENDING sentinel."""
    recommendation = make_recommendation()
    model = RecommendationModelMapper.to_orm(recommendation, generation_id=uuid.uuid4())
    _simulate_flush(model)

    record = RecommendationModelMapper.to_domain(model)

    assert record.decision is None
    assert record.decision_note is None
    assert record.decided_at is None


def test_to_domain_carries_decision_fields_through_when_present(make_recommendation):
    from datetime import datetime, timezone

    from backend.services.recommendation_service.app.domain.recommendation_decision import RecommendationDecision

    recommendation = make_recommendation()
    model = RecommendationModelMapper.to_orm(recommendation, generation_id=uuid.uuid4())
    _simulate_flush(model)
    decided_at = datetime.now(timezone.utc)
    model.decision = RecommendationDecision.DEFERRED
    model.decision_note = "Needs more data."
    model.decided_at = decided_at

    record = RecommendationModelMapper.to_domain(model)

    assert record.decision == RecommendationDecision.DEFERRED
    assert record.decision_note == "Needs more data."
    assert record.decided_at == decided_at
