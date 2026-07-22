import pytest

from backend.services.business_impact_service.app.domain.anomaly_metrics import AnomalyMetrics
from backend.services.business_impact_service.app.domain.incident import Incident
from backend.services.business_impact_service.app.domain.root_cause_summary import RootCauseSummary
from backend.services.business_impact_service.app.domain.trend_metrics import TrendMetrics
from backend.shared.constants.enums.anomaly import AnomalySeverity
from backend.shared.constants.enums.root_cause import RootCause


def _make_incident(
    *,
    incident_id="INC-TEST0001",
    severity=AnomalySeverity.MEDIUM,
    regions=(),
    urgency_levels=(),
) -> Incident:
    """Builds a plain, in-memory Incident for rule/engine unit tests."""
    return Incident(
        incident_id=incident_id,
        severity=severity,
        regions=regions,
        urgency_levels=urgency_levels,
    )


def _make_root_cause(
    *,
    cause=RootCause.UNKNOWN,
    confidence_score=50,
    confidence_level="Medium",
) -> RootCauseSummary:
    """Builds a plain, in-memory RootCauseSummary for rule/engine unit tests."""
    return RootCauseSummary(
        cause=cause,
        confidence_score=confidence_score,
        confidence_level=confidence_level,
    )


def _make_trend_metrics(
    *,
    current_volume=100,
    baseline_volume=100,
    percentage_change=0.0,
) -> TrendMetrics:
    """Builds a plain, in-memory TrendMetrics for rule/engine unit tests."""
    return TrendMetrics(
        current_volume=current_volume,
        baseline_volume=baseline_volume,
        percentage_change=percentage_change,
    )


def _make_anomaly_metrics(
    *,
    anomaly_types=(),
    severity=AnomalySeverity.MEDIUM,
    affected_customer_count=0,
    sla_breach_count=0,
    negative_sentiment_ratio=0.0,
) -> AnomalyMetrics:
    """Builds a plain, in-memory AnomalyMetrics for rule/engine unit tests."""
    return AnomalyMetrics(
        anomaly_types=anomaly_types,
        severity=severity,
        affected_customer_count=affected_customer_count,
        sla_breach_count=sla_breach_count,
        negative_sentiment_ratio=negative_sentiment_ratio,
    )


@pytest.fixture
def make_incident():
    return _make_incident


@pytest.fixture
def make_root_cause():
    return _make_root_cause


@pytest.fixture
def make_trend_metrics():
    return _make_trend_metrics


@pytest.fixture
def make_anomaly_metrics():
    return _make_anomaly_metrics
