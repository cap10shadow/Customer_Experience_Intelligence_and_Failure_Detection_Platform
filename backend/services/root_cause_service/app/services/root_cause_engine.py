from typing import List, Optional

from backend.services.root_cause_service.app.domain.confidence import ConfidenceScore
from backend.services.root_cause_service.app.domain.incident import Incident
from backend.services.root_cause_service.app.domain.root_cause_candidate import RootCauseCandidate
from backend.services.root_cause_service.app.services.explanation import build_explanation, build_unknown_explanation
from backend.services.root_cause_service.app.services.rule_engine import Rule, RuleResult
from backend.services.root_cause_service.app.services.rule_registry import RuleRegistry, default_registry
from backend.shared.constants.enums.root_cause import RootCause

UNKNOWN_RULE_VERSION = "1.0"


class RootCauseEngine:
    """
    Root Cause Rule Engine

    Ownership:
    Owned by the Root Cause Service.

    Operational Purpose:
    Evaluates every registered deterministic rule against a single Incident
    and selects the highest-confidence matching cause. Purely in-memory:
    never queries anomalies, a database, or any repository/API — it only
    ever evaluates the Incident object it is given.

    Philosophy:
    - Deterministic only: rule evaluation and selection never involve
      randomness or probabilistic reasoning. Ties are broken by
      registration order (registry order is the single source of
      precedence), never arbitrarily.
    - Open/closed: new causes are added by registering a new Rule in
      `rule_registry.py`, never by editing this engine's selection logic.
    - Fully explainable: every candidate — including the UNKNOWN fallback —
      carries its evidence, confidence, and the rule version that produced it.
    """

    def __init__(self, registry: Optional[RuleRegistry] = None) -> None:
        self._registry = registry or default_registry()

    def analyze(self, incident: Incident) -> RootCauseCandidate:
        """Evaluates every registered rule against `incident` and returns the best candidate."""
        rules: List[Rule] = self._registry.all_rules()
        results: List[RuleResult] = [rule.evaluate(incident) for rule in rules]
        matched = [result for result in results if result.matched]

        if not matched:
            return self._unknown_candidate()

        best = max(matched, key=lambda result: result.score)
        confidence = ConfidenceScore.from_score(best.score)
        explanation = build_explanation(best, best.evidence, confidence.band)

        return RootCauseCandidate(
            cause=best.cause,
            confidence_score=confidence.score,
            confidence_level=confidence.band,
            evidence=best.evidence,
            explanation=explanation,
            rule_version=best.rule_version,
        )

    def _unknown_candidate(self) -> RootCauseCandidate:
        confidence = ConfidenceScore.from_score(0)
        return RootCauseCandidate(
            cause=RootCause.UNKNOWN,
            confidence_score=confidence.score,
            confidence_level=confidence.band,
            evidence=(),
            explanation=build_unknown_explanation(),
            rule_version=UNKNOWN_RULE_VERSION,
        )
