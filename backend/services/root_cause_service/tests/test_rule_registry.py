from backend.services.root_cause_service.app.services.rule_engine import Rule
from backend.services.root_cause_service.app.services.rule_registry import RuleRegistry, default_registry
from backend.services.root_cause_service.app.services.rules.inventory_rule import InventoryRule
from backend.services.root_cause_service.app.services.rules.logistics_rule import LogisticsRule
from backend.services.root_cause_service.app.services.rules.outage_rule import OutageRule
from backend.services.root_cause_service.app.services.rules.payment_rule import PaymentRule
from backend.services.root_cause_service.app.services.rules.support_rule import SupportRule


def test_default_registry_registers_all_five_built_in_rules():
    registry = default_registry()
    rules = registry.all_rules()
    assert len(rules) == 5
    assert {type(rule) for rule in rules} == {
        PaymentRule,
        LogisticsRule,
        OutageRule,
        InventoryRule,
        SupportRule,
    }


def test_all_rules_returns_fresh_instances_in_registration_order():
    registry = default_registry()
    types_in_order = [type(rule) for rule in registry.all_rules()]
    assert types_in_order == [PaymentRule, LogisticsRule, OutageRule, InventoryRule, SupportRule]


def test_registering_a_new_rule_requires_no_engine_changes():
    class _StubRule(Rule):
        def evaluate(self, incident):
            raise NotImplementedError

    registry = RuleRegistry()
    registry.register(_StubRule)
    rules = registry.all_rules()
    assert len(rules) == 1
    assert isinstance(rules[0], _StubRule)


def test_empty_registry_returns_no_rules():
    registry = RuleRegistry()
    assert registry.all_rules() == []
