from backend.services.evaluation_service.app.domain.confidence_summary import ConfidenceSummary
from backend.services.evaluation_service.app.domain.evaluation import Evaluation
from backend.services.evaluation_service.app.domain.evaluation_metadata import EvaluationMetadata
from backend.services.evaluation_service.app.domain.explainability_assessment import ExplainabilityAssessment
from backend.services.evaluation_service.app.domain.quality_assessment import QualityAssessment
from backend.services.evaluation_service.app.domain.validation_summary import ValidationSummary

EVALUATION_VERSION = "1.0"


class EvaluationBuilder:
    """
    Evaluation Builder

    Operational Purpose:
    The only component responsible for constructing the Evaluation
    Aggregate Root. Assembles the outputs of ValidationEngine,
    QualityEngine, ExplainabilityEngine, and ConfidenceAnalyzer into one
    immutable Evaluation, and stamps it with the current
    `EVALUATION_VERSION`.

    Architectural Boundaries:
    - Enforces the aggregate's one hard invariant: an Evaluation can only
      ever be built from a *successful* ValidationSummary. This is
      construction-time enforcement, not a duplicate of
      EvaluationOrchestrator's own validation-failure short-circuit --
      the Orchestrator's check exists to skip QualityEngine/
      ExplainabilityEngine/ConfidenceAnalyzer entirely when validation
      fails (an optimization and a control-flow decision), while this
      check exists so the Aggregate itself can never be constructed in an
      invalid state, regardless of caller.
    - `previous_evaluation_id` is not accepted as a parameter here: Step 1
      has no persistence or repository layer, so there is no prior record
      to link to yet (see EvaluationMetadata).
    """

    def build(
        self,
        *,
        incident_id: str,
        validation_summary: ValidationSummary,
        quality_assessment: QualityAssessment,
        explainability_assessment: ExplainabilityAssessment,
        confidence_summary: ConfidenceSummary,
    ) -> Evaluation:
        if not incident_id:
            raise ValueError("Cannot build an Evaluation without an incident_id")
        if not validation_summary.is_valid:
            raise ValueError("Cannot build an Evaluation from a failed ValidationSummary")

        return Evaluation(
            incident_id=incident_id,
            validation_summary=validation_summary,
            quality_assessment=quality_assessment,
            explainability_assessment=explainability_assessment,
            confidence_summary=confidence_summary,
            metadata=EvaluationMetadata(evaluation_version=EVALUATION_VERSION),
        )
