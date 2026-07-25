from dataclasses import dataclass

from backend.shared.constants.enums.root_cause import RootCause


@dataclass(frozen=True)
class DomainEvaluationContext:
    """
    The Domain layer's own input contract for one Incident's completed
    intelligence -- ValidationEngine, QualityEngine, ExplainabilityEngine,
    and ConfidenceAnalyzer all depend on this, never on the Application
    layer's `CompletedIntelligence` DTO.

    Architectural Boundaries:
    - Preserves Clean Architecture's dependency direction: the Domain layer
      must not depend on the Application layer. `EvaluationOrchestrator`
      (Application) maps an incoming `CompletedIntelligence` (Application)
      into this object via `EvaluationContextMapper` (Application) before
      calling any Domain engine -- the same Input Mapper boundary already
      used by `root_cause_service`'s `IncidentMapper` and
      `business_impact_service`'s `BusinessImpactInputMapper`.
    - Deliberately field-for-field identical to `CompletedIntelligence`: this
      refinement corrects *which layer owns the input type engines depend
      on*, not the shape of the data itself.
    - `root_cause` reuses the shared `RootCause` enum, the same
      already-established precedent used by `business_impact_service`'s own
      domain-layer `RootCauseSummary`.
    """

    incident_id: str

    root_cause: RootCause
    root_cause_confidence_score: int
    root_cause_explanation: str
    root_cause_evidence_count: int

    business_impact_overall_score: int
    business_impact_overall_severity: str
    business_impact_business_priority: str
    business_impact_confidence: int
    business_impact_explanation: str
