from backend.services.root_cause_service.app.services.rules.support_rule import SupportRule
from backend.shared.constants.enums.anomaly import AnomalyType
from backend.shared.constants.enums.complaint import IssueCategory, UrgencyLabel
from backend.shared.constants.enums.root_cause import RootCause


def test_does_not_match_without_support_category(make_incident):
    incident = make_incident(categories=(IssueCategory.PRODUCT_ISSUE,))
    result = SupportRule().evaluate(incident)
    assert result.matched is False
    assert result.cause == RootCause.CUSTOMER_SUPPORT_DELAY


def test_matches_on_support_category(make_incident):
    incident = make_incident(categories=(IssueCategory.SUPPORT_ISSUE,))
    result = SupportRule().evaluate(incident)
    assert result.matched is True
    assert result.score == 40


def test_score_increases_with_urgency_and_sentiment(make_incident):
    incident = make_incident(
        categories=(IssueCategory.SUPPORT_ISSUE,),
        urgency_levels=(UrgencyLabel.CRITICAL,),
        anomaly_types=(AnomalyType.SENTIMENT_SHIFT,),
    )
    result = SupportRule().evaluate(incident)
    assert result.score == 40 + 20 + 15
    assert len(result.evidence) == 3
