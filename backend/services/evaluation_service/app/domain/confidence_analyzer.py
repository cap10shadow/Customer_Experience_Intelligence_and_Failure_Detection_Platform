from backend.services.evaluation_service.app.domain.confidence_summary import ConfidenceSummary
from backend.services.evaluation_service.app.domain.domain_evaluation_context import DomainEvaluationContext


class ConfidenceAnalyzer:
    """
    Confidence Analyzer

    Operational Purpose:
    Summarizes the confidence values already produced by upstream stages
    (Root Cause, Business Impact) for one Incident. Per ADR-008, it must
    never recalculate or reinterpret confidence -- it only reads the two
    pre-existing values off the DomainEvaluationContext it is given and
    reports them, plus their arithmetic mean as a transparent summary
    statistic.

    Architectural Boundaries:
    - Stateless and side-effect free: depends only on the
      DomainEvaluationContext it is given -- a Domain-layer type, never the
      Application layer's CompletedIntelligence DTO (see
      EvaluationContextMapper).
    - Deterministic: the same input always produces the same
      ConfidenceSummary.
    - Contains no scoring rules, no thresholds, no bands -- unlike
      QualityEngine/ExplainabilityEngine, it performs no evaluation of its
      own, only summarization of values it did not produce.
    """

    def summarize(self, context: DomainEvaluationContext) -> ConfidenceSummary:
        root_cause_confidence = context.root_cause_confidence_score
        business_impact_confidence = context.business_impact_confidence
        average_confidence = (root_cause_confidence + business_impact_confidence) / 2

        return ConfidenceSummary(
            root_cause_confidence=root_cause_confidence,
            business_impact_confidence=business_impact_confidence,
            average_confidence=average_confidence,
        )
