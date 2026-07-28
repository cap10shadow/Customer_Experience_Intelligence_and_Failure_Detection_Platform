import uuid
from typing import Any, Dict, Optional

from backend.services.evaluation_service.app.domain.confidence_summary import ConfidenceSummary
from backend.services.evaluation_service.app.domain.evaluation import Evaluation
from backend.services.evaluation_service.app.domain.evaluation_metadata import EvaluationMetadata
from backend.services.evaluation_service.app.domain.evaluation_rating import EvaluationRating
from backend.services.evaluation_service.app.domain.evaluation_record import EvaluationRecord
from backend.services.evaluation_service.app.domain.explainability_assessment import ExplainabilityAssessment
from backend.services.evaluation_service.app.domain.quality_assessment import QualityAssessment
from backend.services.evaluation_service.app.domain.validation_summary import ValidationSummary
from backend.services.evaluation_service.app.infrastructure.persistence.models.evaluation_model import EvaluationModel


class EvaluationModelMapper:
    """
    Evaluation Model Mapper

    Operational Purpose:
    Translates between the Domain's `Evaluation`/`EvaluationRecord` and
    Infrastructure's `EvaluationModel` (ORM), including JSONB
    serialization/deserialization of every Value Object. The only place
    this boundary is crossed -- `PostgreSQLEvaluationRepository` never
    touches JSONB dict shapes directly, only this mapper.

    Pure translation only -- no business logic. Every field is copied
    verbatim; this mapper never validates, scores, or reinterprets
    anything.
    """

    @staticmethod
    def to_orm(
        evaluation: Evaluation,
        *,
        previous_evaluation_id: Optional[uuid.UUID] = None,
        root_cause_id: Optional[uuid.UUID] = None,
        business_impact_id: Optional[uuid.UUID] = None,
        event_id: Optional[uuid.UUID] = None,
    ) -> EvaluationModel:
        """
        Builds a brand-new EvaluationModel row for an Evaluation being
        persisted for the first time. `previous_evaluation_id` is supplied
        explicitly by the repository (which determines it via
        `get_latest`), not read from `evaluation.metadata` -- the Domain
        Builder always stamps that field `None` (Step 1 has no persistence
        to look it up from).
        """
        return EvaluationModel(
            incident_id=evaluation.incident_id,
            root_cause_id=root_cause_id,
            business_impact_id=business_impact_id,
            event_id=event_id,
            evaluation_version=evaluation.metadata.evaluation_version,
            previous_evaluation_id=previous_evaluation_id,
            validation_summary=EvaluationModelMapper._validation_summary_to_json(evaluation.validation_summary),
            quality_assessment=EvaluationModelMapper._quality_assessment_to_json(evaluation.quality_assessment),
            explainability_assessment=EvaluationModelMapper._explainability_assessment_to_json(
                evaluation.explainability_assessment
            ),
            confidence_summary=EvaluationModelMapper._confidence_summary_to_json(evaluation.confidence_summary),
            evaluation_metadata=EvaluationModelMapper._metadata_to_json(
                evaluation.metadata, previous_evaluation_id=previous_evaluation_id
            ),
        )

    @staticmethod
    def to_domain(model: EvaluationModel) -> EvaluationRecord:
        evaluation = Evaluation(
            incident_id=model.incident_id,
            validation_summary=EvaluationModelMapper._validation_summary_from_json(model.validation_summary),
            quality_assessment=EvaluationModelMapper._quality_assessment_from_json(model.quality_assessment),
            explainability_assessment=EvaluationModelMapper._explainability_assessment_from_json(
                model.explainability_assessment
            ),
            confidence_summary=EvaluationModelMapper._confidence_summary_from_json(model.confidence_summary),
            metadata=EvaluationModelMapper._metadata_from_json(model.evaluation_metadata),
        )
        return EvaluationRecord(
            evaluation_id=model.evaluation_id,
            evaluation=evaluation,
            root_cause_id=model.root_cause_id,
            business_impact_id=model.business_impact_id,
            created_at=model.created_at,
            event_id=model.event_id,
        )

    # ------------------------------------------------------------------
    # ValidationSummary
    # ------------------------------------------------------------------

    @staticmethod
    def _validation_summary_to_json(validation_summary: ValidationSummary) -> Dict[str, Any]:
        return {"is_valid": validation_summary.is_valid, "reasons": list(validation_summary.reasons)}

    @staticmethod
    def _validation_summary_from_json(payload: Dict[str, Any]) -> ValidationSummary:
        return ValidationSummary(is_valid=payload["is_valid"], reasons=tuple(payload["reasons"]))

    # ------------------------------------------------------------------
    # QualityAssessment
    # ------------------------------------------------------------------

    @staticmethod
    def _quality_assessment_to_json(quality_assessment: QualityAssessment) -> Dict[str, Any]:
        return {
            "quality_score": quality_assessment.quality_score,
            "quality_rating": quality_assessment.quality_rating.value,
            "findings": list(quality_assessment.findings),
        }

    @staticmethod
    def _quality_assessment_from_json(payload: Dict[str, Any]) -> QualityAssessment:
        return QualityAssessment(
            quality_score=payload["quality_score"],
            quality_rating=EvaluationRating(payload["quality_rating"]),
            findings=tuple(payload["findings"]),
        )

    # ------------------------------------------------------------------
    # ExplainabilityAssessment
    # ------------------------------------------------------------------

    @staticmethod
    def _explainability_assessment_to_json(explainability_assessment: ExplainabilityAssessment) -> Dict[str, Any]:
        return {
            "explainability_score": explainability_assessment.explainability_score,
            "explainability_rating": explainability_assessment.explainability_rating.value,
            "findings": list(explainability_assessment.findings),
        }

    @staticmethod
    def _explainability_assessment_from_json(payload: Dict[str, Any]) -> ExplainabilityAssessment:
        return ExplainabilityAssessment(
            explainability_score=payload["explainability_score"],
            explainability_rating=EvaluationRating(payload["explainability_rating"]),
            findings=tuple(payload["findings"]),
        )

    # ------------------------------------------------------------------
    # ConfidenceSummary
    # ------------------------------------------------------------------

    @staticmethod
    def _confidence_summary_to_json(confidence_summary: ConfidenceSummary) -> Dict[str, Any]:
        return {
            "root_cause_confidence": confidence_summary.root_cause_confidence,
            "business_impact_confidence": confidence_summary.business_impact_confidence,
            "average_confidence": confidence_summary.average_confidence,
        }

    @staticmethod
    def _confidence_summary_from_json(payload: Dict[str, Any]) -> ConfidenceSummary:
        return ConfidenceSummary(
            root_cause_confidence=payload["root_cause_confidence"],
            business_impact_confidence=payload["business_impact_confidence"],
            average_confidence=payload["average_confidence"],
        )

    # ------------------------------------------------------------------
    # EvaluationMetadata
    # ------------------------------------------------------------------

    @staticmethod
    def _metadata_to_json(metadata: EvaluationMetadata, *, previous_evaluation_id: Optional[uuid.UUID]) -> Dict[str, Any]:
        return {
            "evaluation_version": metadata.evaluation_version,
            "previous_evaluation_id": str(previous_evaluation_id) if previous_evaluation_id else None,
        }

    @staticmethod
    def _metadata_from_json(payload: Dict[str, Any]) -> EvaluationMetadata:
        return EvaluationMetadata(
            evaluation_version=payload["evaluation_version"],
            previous_evaluation_id=payload["previous_evaluation_id"],
        )
