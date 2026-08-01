from dataclasses import dataclass
from typing import Optional

from backend.services.recommendation_service.app.domain.anomaly_intelligence import AnomalyIntelligence
from backend.services.recommendation_service.app.domain.business_impact_summary import BusinessImpactSummary
from backend.services.recommendation_service.app.domain.incident import Incident
from backend.services.recommendation_service.app.domain.nlp_intelligence import NLPIntelligence
from backend.services.recommendation_service.app.domain.root_cause_summary import RootCauseSummary


@dataclass(frozen=True)
class IntelligenceContext:
    """
    Intelligence Context (Domain Value Object)

    Operational Purpose:
    The Recommendation Engine's sole input: a single, immutable snapshot of
    the complete operational intelligence available for one Incident.
    Every Recommendation Rule consumes this exact same snapshot -- rules
    never receive Incident, BusinessImpactSummary, RootCauseSummary,
    NLPIntelligence, or AnomalyIntelligence independently, and never fetch
    any of them on their own.

    Architectural Boundaries:
    - Pure, in-memory, framework-independent. No I/O, no repository, no
      persistence identity -- constructing this from real, persisted
      records is a later step's responsibility (Phase 9 Step 2/3), exactly
      as Business Impact's and Evaluation's own input DTOs were built
      first and wired to real data only in a later step.
    - `incident` and `business_impact` are required: per the frozen domain
      invariant, a Recommendation cannot exist without an Incident and a
      Business Impact. `root_cause`, `nlp_intelligence`, and
      `anomaly_intelligence` are deliberately `Optional` -- an Incident may
      not yet have a confirmed root cause, a representative NLP enrichment,
      or anomaly-level detail attached, and that absence is itself
      meaningful signal to certain rules (see `InvestigateRule`), not an
      error condition.
    """

    incident: Incident
    business_impact: BusinessImpactSummary
    root_cause: Optional[RootCauseSummary] = None
    nlp_intelligence: Optional[NLPIntelligence] = None
    anomaly_intelligence: Optional[AnomalyIntelligence] = None

    def __post_init__(self) -> None:
        if self.incident is None:
            raise ValueError("IntelligenceContext requires an Incident")
        if self.business_impact is None:
            raise ValueError("IntelligenceContext requires a BusinessImpact")
