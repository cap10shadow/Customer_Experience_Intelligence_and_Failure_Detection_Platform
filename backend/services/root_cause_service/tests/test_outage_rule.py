from backend.services.root_cause_service.app.services.rules.outage_rule import OutageRule
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType
from backend.shared.constants.enums.complaint import IssueCategory, UrgencyLabel
from backend.shared.constants.enums.root_cause import RootCause


def test_does_not_match_without_category_or_regional_spike(make_incident):
    incident = make_incident(categories=(IssueCategory.PAYMENT_ISSUE,))
    result = OutageRule().evaluate(incident)
    assert result.matched is False
    assert result.cause == RootCause.SERVICE_OUTAGE


def test_matches_on_operational_failure_category(make_incident):
    incident = make_incident(categories=(IssueCategory.OPERATIONAL_FAILURE,))
    result = OutageRule().evaluate(incident)
    assert result.matched is True
    assert result.score == 40


def test_matches_on_technical_category(make_incident):
    incident = make_incident(categories=(IssueCategory.TECHNICAL_ISSUE,))
    result = OutageRule().evaluate(incident)
    assert result.matched is True


def test_matches_on_regional_spike_alone(make_incident):
    incident = make_incident(anomaly_types=(AnomalyType.REGIONAL_SPIKE,))
    result = OutageRule().evaluate(incident)
    assert result.matched is True
    assert result.score == 15


def test_category_and_region_together_combine_evidence(make_incident):
    incident = make_incident(
        categories=(IssueCategory.OPERATIONAL_FAILURE,),
        anomaly_types=(AnomalyType.REGIONAL_SPIKE,),
    )
    result = OutageRule().evaluate(incident)
    assert result.score == 40 + 15
    assert len(result.evidence) == 2


def test_full_reinforcement_reaches_max_score(make_incident):
    incident = make_incident(
        categories=(IssueCategory.OPERATIONAL_FAILURE,),
        anomaly_types=(AnomalyType.REGIONAL_SPIKE,),
        severity=AnomalySeverity.CRITICAL,
        urgency_levels=(UrgencyLabel.CRITICAL,),
    )
    result = OutageRule().evaluate(incident)
    assert result.score == 100  # 40 + 15 + 25 + 20
