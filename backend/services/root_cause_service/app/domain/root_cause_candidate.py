from dataclasses import dataclass
from typing import Tuple

from backend.services.root_cause_service.app.domain.evidence import Evidence
from backend.shared.constants.enums.root_cause import RootCause


@dataclass(frozen=True)
class RootCauseCandidate:
    """
    The Root Cause Rule Engine's output for one Incident: the most probable
    cause, its confidence, the evidence that produced it, and a
    human-readable explanation. No database IDs, no persistence — this is
    a pure, in-memory value object.
    """
    cause: RootCause
    confidence_score: int
    confidence_level: str
    evidence: Tuple[Evidence, ...]
    explanation: str
    rule_version: str
