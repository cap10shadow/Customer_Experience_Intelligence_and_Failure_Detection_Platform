"""
ORM mapping tests: pure Python round-trip verification of
EvaluationModelMapper's to_orm()/to_domain() translation -- no database
required. Repository-level tests that actually exercise SQL execution live
in test_postgresql_evaluation_repository.py.
"""

import uuid
from datetime import datetime, timezone

from backend.services.evaluation_service.app.domain.evaluation_rating import EvaluationRating
from backend.services.evaluation_service.app.infrastructure.persistence.models.evaluation_model import EvaluationModel
from backend.services.evaluation_service.app.infrastructure.persistence.repositories.evaluation_model_mapper import (
    EvaluationModelMapper,
)


def _simulate_flush(model: EvaluationModel) -> None:
    """Mimics what a real PostgreSQL flush would populate (evaluation_id default, created_at server_default)."""
    model.evaluation_id = uuid.uuid4()
    model.created_at = datetime.now(timezone.utc)


def test_to_orm_maps_every_relational_field(make_evaluation):
    evaluation = make_evaluation()

    model = EvaluationModelMapper.to_orm(evaluation)

    assert isinstance(model, EvaluationModel)
    assert model.incident_id == evaluation.incident_id
    assert model.evaluation_version == evaluation.metadata.evaluation_version
    assert model.previous_evaluation_id is None
    assert model.root_cause_id is None
    assert model.business_impact_id is None


def test_to_orm_accepts_explicit_lineage_and_relational_ids(make_evaluation):
    evaluation = make_evaluation()
    previous_id = uuid.uuid4()
    root_cause_id = uuid.uuid4()
    business_impact_id = uuid.uuid4()

    model = EvaluationModelMapper.to_orm(
        evaluation,
        previous_evaluation_id=previous_id,
        root_cause_id=root_cause_id,
        business_impact_id=business_impact_id,
    )

    assert model.previous_evaluation_id == previous_id
    assert model.root_cause_id == root_cause_id
    assert model.business_impact_id == business_impact_id
    assert model.evaluation_metadata["previous_evaluation_id"] == str(previous_id)


def test_to_orm_serializes_validation_summary_as_jsonb_shape(make_evaluation):
    evaluation = make_evaluation()

    model = EvaluationModelMapper.to_orm(evaluation)

    assert model.validation_summary == {"is_valid": True, "reasons": []}


def test_to_orm_serializes_quality_assessment_as_jsonb_shape(make_evaluation):
    evaluation = make_evaluation()

    model = EvaluationModelMapper.to_orm(evaluation)

    assert model.quality_assessment["quality_score"] == evaluation.quality_assessment.quality_score
    assert model.quality_assessment["quality_rating"] == evaluation.quality_assessment.quality_rating.value
    assert model.quality_assessment["findings"] == list(evaluation.quality_assessment.findings)


def test_to_orm_serializes_explainability_assessment_as_jsonb_shape(make_evaluation):
    evaluation = make_evaluation()

    model = EvaluationModelMapper.to_orm(evaluation)

    assert (
        model.explainability_assessment["explainability_score"]
        == evaluation.explainability_assessment.explainability_score
    )
    assert (
        model.explainability_assessment["explainability_rating"]
        == evaluation.explainability_assessment.explainability_rating.value
    )
    assert model.explainability_assessment["findings"] == list(evaluation.explainability_assessment.findings)


def test_to_orm_serializes_confidence_summary_as_jsonb_shape(make_evaluation):
    evaluation = make_evaluation()

    model = EvaluationModelMapper.to_orm(evaluation)

    assert model.confidence_summary == {
        "root_cause_confidence": evaluation.confidence_summary.root_cause_confidence,
        "business_impact_confidence": evaluation.confidence_summary.business_impact_confidence,
        "average_confidence": evaluation.confidence_summary.average_confidence,
    }


def test_round_trip_to_orm_then_to_domain_preserves_every_field(make_evaluation):
    evaluation = make_evaluation()
    previous_id = uuid.uuid4()
    root_cause_id = uuid.uuid4()
    business_impact_id = uuid.uuid4()

    model = EvaluationModelMapper.to_orm(
        evaluation,
        previous_evaluation_id=previous_id,
        root_cause_id=root_cause_id,
        business_impact_id=business_impact_id,
    )
    _simulate_flush(model)

    record = EvaluationModelMapper.to_domain(model)

    assert record.evaluation_id == model.evaluation_id
    assert record.created_at == model.created_at
    assert record.root_cause_id == root_cause_id
    assert record.business_impact_id == business_impact_id
    assert record.evaluation.incident_id == evaluation.incident_id
    assert record.evaluation.validation_summary == evaluation.validation_summary
    assert record.evaluation.quality_assessment == evaluation.quality_assessment
    assert record.evaluation.explainability_assessment == evaluation.explainability_assessment
    assert record.evaluation.confidence_summary == evaluation.confidence_summary
    assert record.evaluation.metadata.evaluation_version == evaluation.metadata.evaluation_version
    assert record.evaluation.metadata.previous_evaluation_id == str(previous_id)


def test_round_trip_preserves_evaluation_rating_enum_type(make_evaluation):
    """Guards against the JSONB round trip silently degrading EvaluationRating into a bare string."""
    evaluation = make_evaluation()
    model = EvaluationModelMapper.to_orm(evaluation)
    _simulate_flush(model)

    record = EvaluationModelMapper.to_domain(model)

    assert isinstance(record.evaluation.quality_assessment.quality_rating, EvaluationRating)
    assert isinstance(record.evaluation.explainability_assessment.explainability_rating, EvaluationRating)
