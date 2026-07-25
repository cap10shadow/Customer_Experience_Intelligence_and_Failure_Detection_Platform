from typing import Tuple

from backend.services.evaluation_service.app.domain.domain_evaluation_context import DomainEvaluationContext
from backend.services.evaluation_service.app.domain.explainability_assessment import ExplainabilityAssessment
from backend.services.evaluation_service.app.domain.scoring import cap_score, classify_rating

ROOT_CAUSE_EXPLANATION_PRESENT_POINTS = 30
ROOT_CAUSE_HAS_EVIDENCE_POINTS = 20
BUSINESS_IMPACT_EXPLANATION_PRESENT_POINTS = 30
BUSINESS_IMPACT_EXPLANATION_DETAILED_POINTS = 20

SUBSTANTIVE_EXPLANATION_MIN_LENGTH = 10
DETAILED_EXPLANATION_MIN_LENGTH = 50


class ExplainabilityEngine:
    """
    Explainability Engine

    Operational Purpose:
    Independently assesses how well the upstream intelligence (Root Cause +
    Business Impact) explains itself for one Incident, per ADR-006's
    evidence-chain principle -- deterministic, points-based, and
    explainable, mirroring QualityEngine's own scoring discipline.

    Architectural Boundaries:
    - Stateless and side-effect free: depends only on the
      DomainEvaluationContext it is given -- a Domain-layer type, never the
      Application layer's CompletedIntelligence DTO (see
      EvaluationContextMapper).
    - Deterministic: the same input always produces the same
      ExplainabilityAssessment.
    - Never calls or depends on QualityEngine, ConfidenceAnalyzer, or any
      other Evaluation Service component -- independently testable in
      isolation, and always run only after ValidationEngine has already
      confirmed the input is structurally valid.
    """

    def evaluate(self, context: DomainEvaluationContext) -> ExplainabilityAssessment:
        findings: Tuple[str, ...] = ()
        score = 0

        if len(context.root_cause_explanation) > SUBSTANTIVE_EXPLANATION_MIN_LENGTH:
            score += ROOT_CAUSE_EXPLANATION_PRESENT_POINTS
            findings += ("Root cause explanation is present and substantive",)

        if context.root_cause_evidence_count > 0:
            score += ROOT_CAUSE_HAS_EVIDENCE_POINTS
            findings += ("Root cause is backed by at least one evidence entry",)

        if len(context.business_impact_explanation) > SUBSTANTIVE_EXPLANATION_MIN_LENGTH:
            score += BUSINESS_IMPACT_EXPLANATION_PRESENT_POINTS
            findings += ("Business impact explanation is present and substantive",)

        if len(context.business_impact_explanation) > DETAILED_EXPLANATION_MIN_LENGTH:
            score += BUSINESS_IMPACT_EXPLANATION_DETAILED_POINTS
            findings += ("Business impact explanation includes detailed reasoning",)

        if not findings:
            findings = ("No explainability signals were present in the completed intelligence",)

        explainability_score = cap_score(score)
        return ExplainabilityAssessment(
            explainability_score=explainability_score,
            explainability_rating=classify_rating(explainability_score),
            findings=findings,
        )
