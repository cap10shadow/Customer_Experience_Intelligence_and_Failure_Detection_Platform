import pytest

from backend.services.recommendation_service.app.domain.anomaly_intelligence import AnomalyIntelligence
from backend.services.recommendation_service.app.domain.business_impact_summary import BusinessImpactSummary
from backend.services.recommendation_service.app.domain.incident import Incident
from backend.services.recommendation_service.app.domain.intelligence_context import IntelligenceContext
from backend.services.recommendation_service.app.domain.nlp_intelligence import NLPIntelligence
from backend.services.recommendation_service.app.domain.root_cause_summary import RootCauseSummary
from backend.shared.constants.enums.anomaly import AnomalySeverity
from backend.shared.constants.enums.complaint import IssueCategory, SentimentLabel, UrgencyLabel
from backend.shared.constants.enums.root_cause import RootCause

# Distinguishes "root_cause not supplied" (fall back to a confident default)
# from "root_cause explicitly supplied as None" (a genuinely absent root
# cause) -- `None` itself can't serve as that default since it is also a
# valid, meaningful argument value here.
_UNSET = object()


def _make_incident(
    *,
    incident_id="INC-TEST0001",
    severity=AnomalySeverity.MEDIUM,
    categories=(),
    regions=(),
    urgency_levels=(),
) -> Incident:
    """Builds a plain, in-memory Incident for rule/engine unit tests."""
    return Incident(
        incident_id=incident_id,
        severity=severity,
        categories=categories,
        regions=regions,
        urgency_levels=urgency_levels,
    )


def _make_business_impact_summary(
    *,
    business_score=50,
    overall_severity="medium",
    business_priority="medium",
    confidence=50,
    financial_impact="low",
    customer_impact="low",
    operational_impact="low",
    sla_impact="low",
    reputation_impact="low",
) -> BusinessImpactSummary:
    """Builds a plain, in-memory BusinessImpactSummary for rule/engine unit tests.

    Defaults are deliberately non-triggering for every rule (see
    test_recommendation_engine.py's zero-recommendation scenario) --
    individual tests override the specific dimension(s) they need.
    """
    return BusinessImpactSummary(
        business_score=business_score,
        overall_severity=overall_severity,
        business_priority=business_priority,
        confidence=confidence,
        financial_impact=financial_impact,
        customer_impact=customer_impact,
        operational_impact=operational_impact,
        sla_impact=sla_impact,
        reputation_impact=reputation_impact,
    )


def _make_root_cause(
    *,
    cause=RootCause.UNKNOWN,
    confidence_score=80,
    confidence_level="High",
) -> RootCauseSummary:
    """Builds a plain, in-memory RootCauseSummary for rule/engine unit tests."""
    return RootCauseSummary(cause=cause, confidence_score=confidence_score, confidence_level=confidence_level)


def _make_nlp_intelligence(
    *,
    sentiment_label=SentimentLabel.NEUTRAL,
    urgency_label=UrgencyLabel.LOW,
    issue_category=IssueCategory.SUPPORT_ISSUE,
    confidence_score=0.8,
) -> NLPIntelligence:
    """Builds a plain, in-memory NLPIntelligence for rule/engine unit tests."""
    return NLPIntelligence(
        sentiment_label=sentiment_label,
        urgency_label=urgency_label,
        issue_category=issue_category,
        confidence_score=confidence_score,
    )


def _make_anomaly_intelligence(
    *,
    anomaly_types=(),
    severity=AnomalySeverity.LOW,
    affected_customer_count=0,
    sla_breach_count=0,
    negative_sentiment_ratio=0.0,
) -> AnomalyIntelligence:
    """Builds a plain, in-memory AnomalyIntelligence for rule/engine unit tests."""
    return AnomalyIntelligence(
        anomaly_types=anomaly_types,
        severity=severity,
        affected_customer_count=affected_customer_count,
        sla_breach_count=sla_breach_count,
        negative_sentiment_ratio=negative_sentiment_ratio,
    )


def _make_intelligence_context(
    *,
    incident=None,
    business_impact=None,
    root_cause=_UNSET,
    nlp_intelligence=None,
    anomaly_intelligence=None,
) -> IntelligenceContext:
    """
    Builds a plain, in-memory IntelligenceContext for engine/rule unit
    tests. `root_cause` defaults to a confident, known cause (so
    InvestigateRule does not fire unless a test asks for it) -- callers
    that explicitly want a genuinely absent root cause must pass
    `root_cause=None`, which `_UNSET` (not `None`) as the parameter default
    makes distinguishable from "not supplied at all". `nlp_intelligence`
    and `anomaly_intelligence` default to `None` (genuinely absent),
    matching their Optional status on IntelligenceContext itself -- no
    rule in this Step 1 engine treats "not supplied" differently from
    "explicitly None" for those two, so no sentinel is needed for them.
    """
    return IntelligenceContext(
        incident=incident if incident is not None else _make_incident(),
        business_impact=business_impact if business_impact is not None else _make_business_impact_summary(),
        root_cause=_make_root_cause() if root_cause is _UNSET else root_cause,
        nlp_intelligence=nlp_intelligence,
        anomaly_intelligence=anomaly_intelligence,
    )


@pytest.fixture
def make_incident():
    return _make_incident


@pytest.fixture
def make_business_impact_summary():
    return _make_business_impact_summary


@pytest.fixture
def make_root_cause():
    return _make_root_cause


@pytest.fixture
def make_nlp_intelligence():
    return _make_nlp_intelligence


@pytest.fixture
def make_anomaly_intelligence():
    return _make_anomaly_intelligence


@pytest.fixture
def make_intelligence_context():
    return _make_intelligence_context
