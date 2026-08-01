"""
Unit tests for the plain, persistence-independent input value objects
IntelligenceContext is built from: Incident, BusinessImpactSummary,
RootCauseSummary, NLPIntelligence, AnomalyIntelligence. Covers immutability
and sensible defaults -- each is a frozen dataclass with no invariants of
its own beyond what the type system already enforces.
"""

import dataclasses

import pytest

from backend.shared.constants.enums.anomaly import AnomalySeverity
from backend.shared.constants.enums.complaint import IssueCategory, SentimentLabel, UrgencyLabel
from backend.shared.constants.enums.root_cause import RootCause


def test_incident_is_immutable(make_incident):
    incident = make_incident()
    with pytest.raises(dataclasses.FrozenInstanceError):
        incident.incident_id = "changed"


def test_incident_defaults_to_empty_tuples():
    from backend.services.recommendation_service.app.domain.incident import Incident

    incident = Incident(incident_id="INC-1", severity=AnomalySeverity.LOW)

    assert incident.categories == ()
    assert incident.regions == ()
    assert incident.urgency_levels == ()


def test_incident_carries_supplied_fields():
    from backend.services.recommendation_service.app.domain.incident import Incident

    incident = Incident(
        incident_id="INC-1",
        severity=AnomalySeverity.HIGH,
        categories=(IssueCategory.TECHNICAL_ISSUE,),
        regions=("us-east",),
        urgency_levels=(UrgencyLabel.HIGH,),
    )

    assert incident.severity == AnomalySeverity.HIGH
    assert IssueCategory.TECHNICAL_ISSUE in incident.categories
    assert incident.regions == ("us-east",)
    assert incident.urgency_levels == (UrgencyLabel.HIGH,)


def test_business_impact_summary_is_immutable(make_business_impact_summary):
    summary = make_business_impact_summary()
    with pytest.raises(dataclasses.FrozenInstanceError):
        summary.business_score = 999


def test_business_impact_summary_carries_supplied_fields(make_business_impact_summary):
    summary = make_business_impact_summary(overall_severity="critical", sla_impact="high")

    assert summary.overall_severity == "critical"
    assert summary.sla_impact == "high"


def test_root_cause_summary_is_immutable(make_root_cause):
    root_cause = make_root_cause()
    with pytest.raises(dataclasses.FrozenInstanceError):
        root_cause.confidence_score = 0


def test_root_cause_summary_carries_supplied_fields(make_root_cause):
    root_cause = make_root_cause(cause=RootCause.SERVICE_OUTAGE, confidence_score=91)

    assert root_cause.cause == RootCause.SERVICE_OUTAGE
    assert root_cause.confidence_score == 91


def test_nlp_intelligence_is_immutable(make_nlp_intelligence):
    nlp = make_nlp_intelligence()
    with pytest.raises(dataclasses.FrozenInstanceError):
        nlp.sentiment_label = SentimentLabel.POSITIVE


def test_nlp_intelligence_carries_supplied_fields(make_nlp_intelligence):
    nlp = make_nlp_intelligence(sentiment_label=SentimentLabel.HIGHLY_NEGATIVE, issue_category=IssueCategory.REFUND_ISSUE)

    assert nlp.sentiment_label == SentimentLabel.HIGHLY_NEGATIVE
    assert nlp.issue_category == IssueCategory.REFUND_ISSUE


def test_anomaly_intelligence_is_immutable(make_anomaly_intelligence):
    anomaly = make_anomaly_intelligence()
    with pytest.raises(dataclasses.FrozenInstanceError):
        anomaly.sla_breach_count = 99


def test_anomaly_intelligence_defaults_negative_sentiment_ratio_to_zero():
    from backend.services.recommendation_service.app.domain.anomaly_intelligence import AnomalyIntelligence

    anomaly = AnomalyIntelligence(
        anomaly_types=(),
        severity=AnomalySeverity.LOW,
        affected_customer_count=0,
        sla_breach_count=0,
    )

    assert anomaly.negative_sentiment_ratio == 0.0


def test_anomaly_intelligence_carries_supplied_fields(make_anomaly_intelligence):
    anomaly = make_anomaly_intelligence(sla_breach_count=5, affected_customer_count=200)

    assert anomaly.sla_breach_count == 5
    assert anomaly.affected_customer_count == 200
