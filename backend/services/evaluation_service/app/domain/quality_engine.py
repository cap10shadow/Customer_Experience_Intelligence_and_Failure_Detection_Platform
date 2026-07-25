from typing import Tuple

from backend.services.evaluation_service.app.domain.domain_evaluation_context import DomainEvaluationContext
from backend.services.evaluation_service.app.domain.quality_assessment import QualityAssessment
from backend.services.evaluation_service.app.domain.scoring import cap_score, classify_rating
from backend.shared.constants.enums.root_cause import RootCause

ROOT_CAUSE_IDENTIFIED_POINTS = 40
ROOT_CAUSE_HIGH_CONFIDENCE_POINTS = 20
BUSINESS_IMPACT_HIGH_CONFIDENCE_POINTS = 20
BUSINESS_IMPACT_MEASURABLE_SIGNAL_POINTS = 20

HIGH_CONFIDENCE_THRESHOLD = 70


class QualityEngine:
    """
    Quality Engine

    Operational Purpose:
    Independently assesses how complete and substantive the upstream
    intelligence (Root Cause + Business Impact) is for one Incident --
    deterministic, points-based, and explainable, the same evidence-scoring
    discipline used by root_cause_service's rules and
    business_impact_service's ImpactRule implementations.

    Architectural Boundaries:
    - Stateless and side-effect free: depends only on the
      DomainEvaluationContext it is given -- a Domain-layer type, never the
      Application layer's CompletedIntelligence DTO (see
      EvaluationContextMapper).
    - Deterministic: the same input always produces the same
      QualityAssessment.
    - Never calls or depends on ExplainabilityEngine, ConfidenceAnalyzer, or
      any other Evaluation Service component -- independently testable in
      isolation, and always run only after ValidationEngine has already
      confirmed the input is structurally valid.
    """

    def evaluate(self, context: DomainEvaluationContext) -> QualityAssessment:
        findings: Tuple[str, ...] = ()
        score = 0

        if context.root_cause != RootCause.UNKNOWN:
            score += ROOT_CAUSE_IDENTIFIED_POINTS
            findings += ("Root cause was identified rather than left unknown",)

        if context.root_cause_confidence_score >= HIGH_CONFIDENCE_THRESHOLD:
            score += ROOT_CAUSE_HIGH_CONFIDENCE_POINTS
            findings += (f"Root cause confidence is high (>= {HIGH_CONFIDENCE_THRESHOLD})",)

        if context.business_impact_confidence >= HIGH_CONFIDENCE_THRESHOLD:
            score += BUSINESS_IMPACT_HIGH_CONFIDENCE_POINTS
            findings += (f"Business impact confidence is high (>= {HIGH_CONFIDENCE_THRESHOLD})",)

        if context.business_impact_overall_score > 0:
            score += BUSINESS_IMPACT_MEASURABLE_SIGNAL_POINTS
            findings += ("Business impact assessment captured measurable signal",)

        if not findings:
            findings = ("No quality signals were present in the completed intelligence",)

        quality_score = cap_score(score)
        return QualityAssessment(
            quality_score=quality_score,
            quality_rating=classify_rating(quality_score),
            findings=findings,
        )
