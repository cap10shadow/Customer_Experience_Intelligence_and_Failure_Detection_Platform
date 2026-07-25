from dataclasses import dataclass

from backend.shared.constants.enums.root_cause import RootCause


@dataclass(frozen=True)
class CompletedIntelligence:
    """
    CompletedIntelligence DTO

    Operational Purpose:
    The Evaluation Service's sole input: a plain, self-contained snapshot of
    one Incident's completed Root Cause and Business Impact intelligence.
    In the full architecture this is what an out-of-band Business Impact
    completion event carries (Phase 8 Step 2's event consumer); Step 1
    accepts it as a plain, already-constructed value and performs no event
    handling, no I/O, and no cross-service calls of its own.

    Architectural Boundaries:
    - Deliberately NOT the Root Cause Service's or Business Impact
      Service's own domain/ORM objects: the Evaluation Service must remain
      independently deployable and must never import another service's
      domain classes (see DATA-002) -- it only ever evaluates the plain
      object it is handed. A later step is responsible for constructing
      this from real, persisted Root Cause and Business Impact records.
    - `root_cause` reuses the shared `RootCause` enum (already a
      cross-service, shared-enum precedent -- Business Impact Service's own
      `RootCauseSummary` does the same); `business_impact_overall_severity`
      and `business_impact_business_priority` are deliberately plain `str`,
      not Business Impact Service's local `ImpactLevel`/`BusinessPriority`
      enums, since those are that service's own domain-local types and must
      not be imported here.
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
