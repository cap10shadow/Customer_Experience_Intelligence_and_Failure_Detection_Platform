from dataclasses import dataclass

from backend.shared.constants.enums.root_cause import RootCause


@dataclass(frozen=True)
class RootCauseSummary:
    """
    Plain, persistence-independent view of a Phase 6 root-cause result, as
    seen by the Business Impact Engine.

    Deliberately NOT the Root Cause Service's `RootCauseCandidate`: this
    engine must never import across a service boundary -- it only ever
    evaluates the plain object it is handed. A later step is responsible
    for constructing this from a real RootCause record.
    """

    cause: RootCause
    confidence_score: int
    confidence_level: str
