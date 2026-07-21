from typing import List, Type

from backend.services.root_cause_service.app.services.rule_engine import Rule
from backend.services.root_cause_service.app.services.rules.inventory_rule import InventoryRule
from backend.services.root_cause_service.app.services.rules.logistics_rule import LogisticsRule
from backend.services.root_cause_service.app.services.rules.outage_rule import OutageRule
from backend.services.root_cause_service.app.services.rules.payment_rule import PaymentRule
from backend.services.root_cause_service.app.services.rules.support_rule import SupportRule


class RuleRegistry:
    """
    Registers every available root-cause rule.

    The Root Cause Engine iterates this registry rather than hardcoding
    rule selection — adding a new rule requires only registering its class
    here, never editing the engine (open/closed principle).
    """

    def __init__(self) -> None:
        self._rule_classes: List[Type[Rule]] = []

    def register(self, rule_class: Type[Rule]) -> None:
        self._rule_classes.append(rule_class)

    def all_rules(self) -> List[Rule]:
        """Instantiates every registered rule, in registration order."""
        return [rule_class() for rule_class in self._rule_classes]


def default_registry() -> RuleRegistry:
    """Builds the registry with every built-in Phase 6 Step 1 rule registered."""
    registry = RuleRegistry()
    registry.register(PaymentRule)
    registry.register(LogisticsRule)
    registry.register(OutageRule)
    registry.register(InventoryRule)
    registry.register(SupportRule)
    return registry
