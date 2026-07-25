import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel

from backend.services.evaluation_service.app.domain.evaluation_rating import EvaluationRating
from backend.services.evaluation_service.app.domain.evaluation_record import EvaluationRecord


class ValidationSummaryResponse(BaseModel):
    """The persisted ValidationSummary that gated this Evaluation's construction (always valid -- a failed validation is never persisted)."""
    is_valid: bool
    reasons: List[str]


class QualityAssessmentResponse(BaseModel):
    quality_score: int
    quality_rating: EvaluationRating
    findings: List[str]


class ExplainabilityAssessmentResponse(BaseModel):
    explainability_score: int
    explainability_rating: EvaluationRating
    findings: List[str]


class ConfidenceSummaryResponse(BaseModel):
    root_cause_confidence: int
    business_impact_confidence: int
    average_confidence: float


class EvaluationResponse(BaseModel):
    """
    Full explainable snapshot of a persisted Evaluation.

    Built explicitly from an `EvaluationRecord` via `from_record` rather
    than `model_validate(..., from_attributes=True)`: the Domain's
    `EvaluationRecord` deliberately nests identity (`evaluation_id`) and
    the `Evaluation` aggregate (`incident_id`, the five Value Objects)
    separately -- see `EvaluationRecord`'s own docstring -- so this
    response flattens that nesting explicitly rather than fighting
    Pydantic's single-level attribute matching.
    """

    evaluation_id: uuid.UUID
    incident_id: str
    root_cause_id: Optional[uuid.UUID] = None
    business_impact_id: Optional[uuid.UUID] = None
    evaluation_version: str
    previous_evaluation_id: Optional[str] = None
    created_at: datetime
    validation_summary: ValidationSummaryResponse
    quality_assessment: QualityAssessmentResponse
    explainability_assessment: ExplainabilityAssessmentResponse
    confidence_summary: ConfidenceSummaryResponse

    @staticmethod
    def from_record(record: EvaluationRecord) -> "EvaluationResponse":
        evaluation = record.evaluation
        return EvaluationResponse(
            evaluation_id=record.evaluation_id,
            incident_id=evaluation.incident_id,
            root_cause_id=record.root_cause_id,
            business_impact_id=record.business_impact_id,
            evaluation_version=evaluation.metadata.evaluation_version,
            previous_evaluation_id=evaluation.metadata.previous_evaluation_id,
            created_at=record.created_at,
            validation_summary=ValidationSummaryResponse(
                is_valid=evaluation.validation_summary.is_valid,
                reasons=list(evaluation.validation_summary.reasons),
            ),
            quality_assessment=QualityAssessmentResponse(
                quality_score=evaluation.quality_assessment.quality_score,
                quality_rating=evaluation.quality_assessment.quality_rating,
                findings=list(evaluation.quality_assessment.findings),
            ),
            explainability_assessment=ExplainabilityAssessmentResponse(
                explainability_score=evaluation.explainability_assessment.explainability_score,
                explainability_rating=evaluation.explainability_assessment.explainability_rating,
                findings=list(evaluation.explainability_assessment.findings),
            ),
            confidence_summary=ConfidenceSummaryResponse(
                root_cause_confidence=evaluation.confidence_summary.root_cause_confidence,
                business_impact_confidence=evaluation.confidence_summary.business_impact_confidence,
                average_confidence=evaluation.confidence_summary.average_confidence,
            ),
        )


class EvaluationStatisticsResponse(BaseModel):
    """Aggregate statistics computed across all persisted Evaluations (see EvaluationStatisticsService)."""
    total_count: int
    quality_rating_counts: Dict[str, int]
    explainability_rating_counts: Dict[str, int]
    average_quality_score: float
    average_explainability_score: float
    average_confidence: float
