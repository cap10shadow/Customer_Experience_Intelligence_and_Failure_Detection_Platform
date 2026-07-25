import dataclasses

import pytest

from backend.services.evaluation_service.app.domain.confidence_summary import ConfidenceSummary
from backend.services.evaluation_service.app.domain.evaluation_builder import EVALUATION_VERSION, EvaluationBuilder
from backend.services.evaluation_service.app.domain.evaluation_rating import EvaluationRating
from backend.services.evaluation_service.app.domain.explainability_assessment import ExplainabilityAssessment
from backend.services.evaluation_service.app.domain.quality_assessment import QualityAssessment
from backend.services.evaluation_service.app.domain.validation_summary import ValidationSummary


def _valid_inputs(incident_id="INC-TEST0001"):
    return dict(
        incident_id=incident_id,
        validation_summary=ValidationSummary(is_valid=True),
        quality_assessment=QualityAssessment(quality_score=80, quality_rating=EvaluationRating.HIGH, findings=("ok",)),
        explainability_assessment=ExplainabilityAssessment(
            explainability_score=70, explainability_rating=EvaluationRating.MEDIUM, findings=("ok",)
        ),
        confidence_summary=ConfidenceSummary(root_cause_confidence=80, business_impact_confidence=70, average_confidence=75.0),
    )


def test_builds_a_complete_evaluation():
    evaluation = EvaluationBuilder().build(**_valid_inputs())

    assert evaluation.incident_id == "INC-TEST0001"
    assert evaluation.quality_assessment.quality_score == 80
    assert evaluation.explainability_assessment.explainability_score == 70
    assert evaluation.confidence_summary.average_confidence == 75.0
    assert evaluation.metadata.evaluation_version == EVALUATION_VERSION
    assert evaluation.metadata.previous_evaluation_id is None


def test_rejects_a_failed_validation_summary():
    inputs = _valid_inputs()
    inputs["validation_summary"] = ValidationSummary(is_valid=False, reasons=("incident_id is missing",))

    with pytest.raises(ValueError, match="failed ValidationSummary"):
        EvaluationBuilder().build(**inputs)


def test_rejects_a_missing_incident_id():
    inputs = _valid_inputs(incident_id="")

    with pytest.raises(ValueError, match="incident_id"):
        EvaluationBuilder().build(**inputs)


def test_is_deterministic():
    inputs = _valid_inputs()

    first = EvaluationBuilder().build(**inputs)
    second = EvaluationBuilder().build(**inputs)

    assert first == second


# ------------------------------------------------------------------
# Immutability
# ------------------------------------------------------------------

def test_evaluation_aggregate_is_immutable():
    evaluation = EvaluationBuilder().build(**_valid_inputs())

    with pytest.raises(dataclasses.FrozenInstanceError):
        evaluation.incident_id = "INC-OTHER"  # type: ignore[misc]


def test_validation_summary_is_immutable():
    summary = ValidationSummary(is_valid=True)

    with pytest.raises(dataclasses.FrozenInstanceError):
        summary.is_valid = False  # type: ignore[misc]


def test_quality_assessment_is_immutable():
    assessment = QualityAssessment(quality_score=50, quality_rating=EvaluationRating.MEDIUM, findings=())

    with pytest.raises(dataclasses.FrozenInstanceError):
        assessment.quality_score = 100  # type: ignore[misc]


def test_explainability_assessment_is_immutable():
    assessment = ExplainabilityAssessment(explainability_score=50, explainability_rating=EvaluationRating.MEDIUM, findings=())

    with pytest.raises(dataclasses.FrozenInstanceError):
        assessment.explainability_score = 100  # type: ignore[misc]


def test_confidence_summary_is_immutable():
    summary = ConfidenceSummary(root_cause_confidence=50, business_impact_confidence=50, average_confidence=50.0)

    with pytest.raises(dataclasses.FrozenInstanceError):
        summary.average_confidence = 0.0  # type: ignore[misc]


def test_evaluation_metadata_is_immutable():
    evaluation = EvaluationBuilder().build(**_valid_inputs())

    with pytest.raises(dataclasses.FrozenInstanceError):
        evaluation.metadata.evaluation_version = "2.0"  # type: ignore[misc]
