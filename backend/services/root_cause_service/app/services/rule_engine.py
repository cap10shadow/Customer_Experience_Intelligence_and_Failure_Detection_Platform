from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Tuple

from backend.services.root_cause_service.app.domain.evidence import Evidence
from backend.services.root_cause_service.app.domain.incident import Incident
from backend.shared.constants.enums.root_cause import RootCause


@dataclass(frozen=True)
class RuleResult:
    """
    A single rule's verdict for one Incident. Purely an in-memory
    intermediate the Root Cause Engine selects among — never persisted.
    """
    matched: bool
    cause: RootCause
    score: int
    evidence: Tuple[Evidence, ...]
    rule_version: str


class Rule(ABC):
    """
    Base for a single, independent root-cause rule.

    Architectural Boundaries:
    - A rule must never mutate the Incident it receives.
    - A rule must never access persistence, anomalies, or any API — it
      evaluates only the Incident object passed to `evaluate`.
    - Every rule exposes `RULE_VERSION` and `CAUSE`; both are echoed back
      on every `RuleResult` it produces (matched or not) for full
      explainability and auditability.
    """

    RULE_VERSION: ClassVar[str] = "1.0"
    CAUSE: ClassVar[RootCause]

    @abstractmethod
    def evaluate(self, incident: Incident) -> RuleResult:
        """Evaluates this rule against `incident` and returns its verdict."""
        raise NotImplementedError
