from dataclasses import dataclass

from backend.shared.constants.enums.root_cause import RootCause


@dataclass(frozen=True)
class RootCauseSummary:
    """
    Plain, persistence-independent view of a Phase 6 root-cause result, as
    seen by the Recommendation Engine.

    Deliberately NOT the Root Cause Service's `RootCauseCandidate` (nor
    Business Impact's own identically-purposed `RootCauseSummary`): this
    engine must never import across a service boundary -- it only ever
    evaluates the plain object it is handed. `RootCause` is a genuinely
    shared enum (`backend.shared.constants.enums.root_cause`), already the
    established cross-service precedent (Business Impact Service's own
    `RootCauseSummary` does the same). A later step is responsible for
    constructing this from a real RootCause record.

    Optional on `IntelligenceContext`: an Incident may not yet have a
    confirmed root cause -- the absence of one is itself meaningful signal
    (see `InvestigateRule`), not an error.
    """

    cause: RootCause
    confidence_score: int
    confidence_level: str
