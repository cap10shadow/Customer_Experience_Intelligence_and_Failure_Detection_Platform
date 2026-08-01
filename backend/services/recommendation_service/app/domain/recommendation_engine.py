from typing import List, Optional, Sequence, Tuple

from backend.services.recommendation_service.app.domain.intelligence_context import IntelligenceContext
from backend.services.recommendation_service.app.domain.recommendation import Recommendation
from backend.services.recommendation_service.app.domain.recommendation_consolidator import RecommendationConsolidator
from backend.services.recommendation_service.app.domain.recommendation_rule import RecommendationRule
from backend.services.recommendation_service.app.domain.rules.customer_communication_rule import (
    CustomerCommunicationRule,
)
from backend.services.recommendation_service.app.domain.rules.escalation_rule import EscalationRule
from backend.services.recommendation_service.app.domain.rules.infrastructure_action_rule import (
    InfrastructureActionRule,
)
from backend.services.recommendation_service.app.domain.rules.investigate_rule import InvestigateRule
from backend.services.recommendation_service.app.domain.rules.mitigation_rule import MitigationRule
from backend.services.recommendation_service.app.domain.rules.monitor_rule import MonitorRule
from backend.services.recommendation_service.app.domain.rules.operational_action_rule import OperationalActionRule
from backend.services.recommendation_service.app.domain.rules.sla_protection_rule import SLAProtectionRule


def default_rules() -> Tuple[RecommendationRule, ...]:
    """
    Builds the built-in Phase 9 Step 1 rule set -- one rule per
    RecommendationCategory. Order here is exactly the engine's rule
    evaluation order, the last tiebreak in the frozen precedence chain.
    """
    return (
        EscalationRule(),
        MitigationRule(),
        SLAProtectionRule(),
        InfrastructureActionRule(),
        OperationalActionRule(),
        CustomerCommunicationRule(),
        InvestigateRule(),
        MonitorRule(),
    )


class RecommendationEngine:
    """
    Recommendation Decision Engine

    Ownership:
    Owned by the Recommendation Service.

    Operational Purpose:
    Evaluates every supplied RecommendationRule against a single
    IntelligenceContext, collects their raw output, and hands it to the
    RecommendationConsolidator to produce the final, deterministic
    Recommendation collection. Purely in-memory: never queries a database
    or any repository/API.

    Philosophy:
    - Deterministic only: no randomness, no ML, no probabilistic reasoning.
      Identical `IntelligenceContext` input always produces an identical
      output collection.
    - Open/closed: the engine depends only on the RecommendationRule
      abstraction, never on concrete rule classes -- it is constructed with
      whatever rules it is given, so adding a new rule never requires
      editing this class.
    - Side-effect free: `generate()` never mutates its input and never
      mutates any collaborator's state between calls.
    """

    def __init__(
        self,
        rules: Sequence[RecommendationRule],
        consolidator: Optional[RecommendationConsolidator] = None,
    ) -> None:
        self._rules = tuple(rules)
        self._consolidator = consolidator or RecommendationConsolidator()

    def generate(self, context: IntelligenceContext) -> Tuple[Recommendation, ...]:
        """Runs every registered rule against `context`, in rule order, and returns the final consolidated collection."""
        raw_recommendations: List[Recommendation] = []
        for rule in self._rules:
            raw_recommendations.extend(rule.evaluate(context))
        return self._consolidator.consolidate(raw_recommendations)
