from typing import List, Tuple

from backend.services.evaluation_service.app.domain.domain_evaluation_context import DomainEvaluationContext
from backend.services.evaluation_service.app.domain.validation_summary import ValidationSummary

MIN_SCORE = 0
MAX_SCORE = 100


class ValidationEngine:
    """
    Validation Engine

    Operational Purpose:
    The first, gating stage of the Evaluation pipeline. Checks that a
    DomainEvaluationContext is structurally complete and well-formed enough
    to be evaluated at all -- never a judgement of intelligence *quality*
    (that is QualityEngine's responsibility) or *explainability*
    (ExplainabilityEngine's responsibility), only of structural validity.

    Architectural Boundaries:
    - Stateless and side-effect free: depends only on the
      DomainEvaluationContext it is given -- a Domain-layer type, never the
      Application layer's CompletedIntelligence DTO (see
      EvaluationContextMapper).
    - Deterministic: the same input always produces the same
      ValidationSummary.
    - When validation fails, the EvaluationOrchestrator returns this
      engine's ValidationSummary directly and never proceeds to
      QualityEngine, ExplainabilityEngine, ConfidenceAnalyzer, or
      EvaluationBuilder.
    """

    def validate(self, context: DomainEvaluationContext) -> ValidationSummary:
        reasons: List[str] = []

        if not context.incident_id:
            reasons.append("incident_id is missing")

        if not (MIN_SCORE <= context.root_cause_confidence_score <= MAX_SCORE):
            reasons.append(
                f"root_cause_confidence_score must be between {MIN_SCORE} and {MAX_SCORE} "
                f"(got {context.root_cause_confidence_score})"
            )

        if not context.root_cause_explanation:
            reasons.append("root_cause_explanation is missing")

        if not (MIN_SCORE <= context.business_impact_overall_score <= MAX_SCORE):
            reasons.append(
                f"business_impact_overall_score must be between {MIN_SCORE} and {MAX_SCORE} "
                f"(got {context.business_impact_overall_score})"
            )

        if not (MIN_SCORE <= context.business_impact_confidence <= MAX_SCORE):
            reasons.append(
                f"business_impact_confidence must be between {MIN_SCORE} and {MAX_SCORE} "
                f"(got {context.business_impact_confidence})"
            )

        if not context.business_impact_explanation:
            reasons.append("business_impact_explanation is missing")

        reasons_tuple: Tuple[str, ...] = tuple(reasons)
        return ValidationSummary(is_valid=len(reasons_tuple) == 0, reasons=reasons_tuple)
