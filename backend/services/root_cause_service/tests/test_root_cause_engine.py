from backend.services.root_cause_service.app.services.rule_engine import Rule, RuleResult
from backend.services.root_cause_service.app.services.rule_registry import RuleRegistry
from backend.services.root_cause_service.app.services.root_cause_engine import RootCauseEngine
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType
from backend.shared.constants.enums.complaint import IssueCategory, UrgencyLabel
from backend.shared.constants.enums.root_cause import RootCause


def test_returns_unknown_when_no_rule_matches(make_incident):
    engine = RootCauseEngine()
    incident = make_incident(categories=(), anomaly_types=())

    candidate = engine.analyze(incident)

    assert candidate.cause == RootCause.UNKNOWN
    assert candidate.confidence_score == 0
    assert candidate.confidence_level == "Weak"
    assert candidate.evidence == ()
    assert "unknown" in candidate.explanation.lower()


def test_selects_the_single_matching_rule(make_incident):
    engine = RootCauseEngine()
    incident = make_incident(categories=(IssueCategory.PRODUCT_ISSUE,))

    candidate = engine.analyze(incident)

    assert candidate.cause == RootCause.INVENTORY_SHORTAGE
    assert candidate.confidence_score == 40
    assert candidate.confidence_level == "Low"
    assert candidate.rule_version == "1.0"


def test_selects_highest_confidence_when_multiple_rules_match(make_incident):
    engine = RootCauseEngine()
    # Both Payment and Outage match the shared category/severity/urgency
    # signals (40 + 25 + 20 = 85 each), but only Outage also checks for a
    # regional spike (+15), giving it a clear, unambiguous 100 vs 85 win.
    incident = make_incident(
        categories=(IssueCategory.PAYMENT_ISSUE, IssueCategory.OPERATIONAL_FAILURE),
        severity=AnomalySeverity.CRITICAL,
        urgency_levels=(UrgencyLabel.CRITICAL,),
        anomaly_types=(AnomalyType.REGIONAL_SPIKE,),
    )

    candidate = engine.analyze(incident)

    assert candidate.cause == RootCause.SERVICE_OUTAGE
    assert candidate.confidence_score == 100
    assert candidate.confidence_level == "Very High"


def test_tie_breaking_is_deterministic_by_registration_order(make_incident):
    class _AlwaysMatchesA(Rule):
        RULE_VERSION = "1.0"
        CAUSE = RootCause.PAYMENT_GATEWAY_FAILURE

        def evaluate(self, incident):
            return RuleResult(matched=True, cause=self.CAUSE, score=50, evidence=(), rule_version=self.RULE_VERSION)

    class _AlwaysMatchesB(Rule):
        RULE_VERSION = "1.0"
        CAUSE = RootCause.LOGISTICS_DELAY

        def evaluate(self, incident):
            return RuleResult(matched=True, cause=self.CAUSE, score=50, evidence=(), rule_version=self.RULE_VERSION)

    registry = RuleRegistry()
    registry.register(_AlwaysMatchesA)
    registry.register(_AlwaysMatchesB)
    engine = RootCauseEngine(registry=registry)

    first_run = engine.analyze(make_incident())
    second_run = engine.analyze(make_incident())

    # Same tie every time -> repeatable, deterministic selection (first
    # registered rule wins ties), never random.
    assert first_run.cause == RootCause.PAYMENT_GATEWAY_FAILURE
    assert second_run.cause == RootCause.PAYMENT_GATEWAY_FAILURE


def test_candidate_carries_full_explainability(make_incident):
    engine = RootCauseEngine()
    incident = make_incident(
        categories=(IssueCategory.SUPPORT_ISSUE,),
        urgency_levels=(UrgencyLabel.HIGH,),
        anomaly_types=(AnomalyType.SENTIMENT_SHIFT,),
    )

    candidate = engine.analyze(incident)

    assert candidate.cause == RootCause.CUSTOMER_SUPPORT_DELAY
    assert candidate.confidence_score == 75
    assert candidate.confidence_level == "High"
    assert len(candidate.evidence) == 3
    assert candidate.rule_version == "1.0"
    assert "customer_support_delay" in candidate.explanation


def test_engine_never_mutates_the_incident_it_analyzes(make_incident):
    engine = RootCauseEngine()
    incident = make_incident(categories=(IssueCategory.PAYMENT_ISSUE,))
    original = incident

    engine.analyze(incident)

    assert incident is original
    assert incident.categories == (IssueCategory.PAYMENT_ISSUE,)


def test_custom_registry_is_used_instead_of_default(make_incident):
    registry = RuleRegistry()  # deliberately empty
    engine = RootCauseEngine(registry=registry)

    candidate = engine.analyze(make_incident(categories=(IssueCategory.PAYMENT_ISSUE,)))

    assert candidate.cause == RootCause.UNKNOWN
