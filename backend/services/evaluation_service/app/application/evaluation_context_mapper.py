from backend.services.evaluation_service.app.application.completed_intelligence import CompletedIntelligence
from backend.services.evaluation_service.app.domain.domain_evaluation_context import DomainEvaluationContext


class EvaluationContextMapper:
    """
    Evaluation Context Mapper

    Operational Purpose:
    Translates a `CompletedIntelligence` (Application-layer DTO) into a
    `DomainEvaluationContext` (Domain-layer value object). This mapper is
    the only place that boundary is crossed -- it is the sole reason the
    Domain layer's engines never need to import `CompletedIntelligence`
    themselves, preserving Clean Architecture's dependency direction
    (Domain must never depend on Application).

    Pure translation only -- no business logic. Every field is copied
    verbatim; this mapper never validates, scores, or reinterprets
    anything (ValidationEngine, QualityEngine, ExplainabilityEngine, and
    ConfidenceAnalyzer own those responsibilities entirely).
    """

    @staticmethod
    def to_domain(completed_intelligence: CompletedIntelligence) -> DomainEvaluationContext:
        return DomainEvaluationContext(
            incident_id=completed_intelligence.incident_id,
            root_cause=completed_intelligence.root_cause,
            root_cause_confidence_score=completed_intelligence.root_cause_confidence_score,
            root_cause_explanation=completed_intelligence.root_cause_explanation,
            root_cause_evidence_count=completed_intelligence.root_cause_evidence_count,
            business_impact_overall_score=completed_intelligence.business_impact_overall_score,
            business_impact_overall_severity=completed_intelligence.business_impact_overall_severity,
            business_impact_business_priority=completed_intelligence.business_impact_business_priority,
            business_impact_confidence=completed_intelligence.business_impact_confidence,
            business_impact_explanation=completed_intelligence.business_impact_explanation,
        )
