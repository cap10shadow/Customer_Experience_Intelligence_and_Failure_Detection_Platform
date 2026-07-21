from backend.services.root_cause_service.app.services.rules.payment_rule import PaymentRule
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType
from backend.shared.constants.enums.complaint import IssueCategory, UrgencyLabel
from backend.shared.constants.enums.root_cause import RootCause


def test_does_not_match_without_payment_category(make_incident):
    incident = make_incident(categories=(IssueCategory.DELIVERY_ISSUE,))
    result = PaymentRule().evaluate(incident)
    assert result.matched is False
    assert result.score == 0
    assert result.evidence == ()
    assert result.cause == RootCause.PAYMENT_GATEWAY_FAILURE
    assert result.rule_version == "1.0"


def test_matches_on_category_alone(make_incident):
    incident = make_incident(categories=(IssueCategory.PAYMENT_ISSUE,))
    result = PaymentRule().evaluate(incident)
    assert result.matched is True
    assert result.score == 40
    assert len(result.evidence) == 1


def test_score_increases_with_reinforcing_signals(make_incident):
    incident = make_incident(
        categories=(IssueCategory.PAYMENT_ISSUE,),
        severity=AnomalySeverity.CRITICAL,
        urgency_levels=(UrgencyLabel.CRITICAL,),
        anomaly_types=(AnomalyType.SENTIMENT_SHIFT,),
    )
    result = PaymentRule().evaluate(incident)
    assert result.matched is True
    assert result.score == 100  # 40 + 25 + 20 + 15
    assert len(result.evidence) == 4


def test_rule_never_mutates_incident(make_incident):
    incident = make_incident(categories=(IssueCategory.PAYMENT_ISSUE,))
    PaymentRule().evaluate(incident)
    assert incident.categories == (IssueCategory.PAYMENT_ISSUE,)  # unchanged (frozen dataclass anyway)
