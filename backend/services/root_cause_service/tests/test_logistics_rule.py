from backend.services.root_cause_service.app.services.rules.logistics_rule import LogisticsRule
from backend.shared.constants.enums.anomaly import AnomalyType
from backend.shared.constants.enums.complaint import IssueCategory, UrgencyLabel
from backend.shared.constants.enums.root_cause import RootCause


def test_does_not_match_without_logistics_category(make_incident):
    incident = make_incident(categories=(IssueCategory.PAYMENT_ISSUE,))
    result = LogisticsRule().evaluate(incident)
    assert result.matched is False
    assert result.cause == RootCause.LOGISTICS_DELAY


def test_matches_delivery_category(make_incident):
    incident = make_incident(categories=(IssueCategory.DELIVERY_ISSUE,))
    result = LogisticsRule().evaluate(incident)
    assert result.matched is True
    assert result.score == 40


def test_matches_service_delay_category(make_incident):
    incident = make_incident(categories=(IssueCategory.SERVICE_DELAY,))
    result = LogisticsRule().evaluate(incident)
    assert result.matched is True


def test_score_increases_with_region_and_urgency(make_incident):
    incident = make_incident(
        categories=(IssueCategory.DELIVERY_ISSUE,),
        anomaly_types=(AnomalyType.REGIONAL_SPIKE,),
        urgency_levels=(UrgencyLabel.HIGH,),
    )
    result = LogisticsRule().evaluate(incident)
    assert result.score == 40 + 15 + 20
    assert len(result.evidence) == 3
