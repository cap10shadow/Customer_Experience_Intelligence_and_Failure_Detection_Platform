import pytest

from backend.services.root_cause_service.app.domain.incident import Incident
from backend.shared.constants.enums.anomaly import AnomalySeverity


def _make_incident(
    *,
    incident_key="INC-TEST0001",
    title="Test Incident",
    summary="test summary",
    severity=AnomalySeverity.MEDIUM,
    confidence_score=50,
    categories=(),
    regions=(),
    urgency_levels=(),
    anomaly_types=(),
) -> Incident:
    """Builds a plain, in-memory Incident for rule/specification/engine unit tests."""
    return Incident(
        incident_key=incident_key,
        title=title,
        summary=summary,
        severity=severity,
        confidence_score=confidence_score,
        categories=categories,
        regions=regions,
        urgency_levels=urgency_levels,
        anomaly_types=anomaly_types,
    )


@pytest.fixture
def make_incident():
    return _make_incident
