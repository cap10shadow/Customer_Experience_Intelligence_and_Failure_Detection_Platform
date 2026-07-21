import uuid

from backend.services.root_cause_service.app.mappers.incident_mapper import IncidentMapper
from backend.services.root_cause_service.app.repositories.incident_read_repository import (
    PersistedActiveAnomaly,
    PersistedIncident,
)
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType
from backend.shared.constants.enums.incident import IncidentStatus
from backend.shared.constants.enums.complaint import IssueCategory, UrgencyLabel


def _persisted_anomaly(type_, entity_type, entity_value):
    return PersistedActiveAnomaly(id=uuid.uuid4(), type=type_, entity_type=entity_type, entity_value=entity_value)


def test_maps_basic_incident_fields():
    persisted = PersistedIncident(
        id=uuid.uuid4(),
        incident_key="INC-ABCD1234",
        title="South Regional Incident",
        summary="test summary",
        severity=AnomalySeverity.CRITICAL,
        status=IncidentStatus.OPEN,
        confidence_score=85,
        anomalies=(),
    )

    incident = IncidentMapper.to_domain(persisted)

    assert incident.incident_key == "INC-ABCD1234"
    assert incident.title == "South Regional Incident"
    assert incident.summary == "test summary"
    assert incident.severity == AnomalySeverity.CRITICAL
    assert incident.confidence_score == 85
    assert incident.categories == ()
    assert incident.regions == ()
    assert incident.urgency_levels == ()
    assert incident.anomaly_types == ()


def test_derives_categories_from_category_scoped_anomalies():
    persisted = PersistedIncident(
        id=uuid.uuid4(),
        incident_key="INC-1",
        title="t",
        summary="s",
        severity=AnomalySeverity.HIGH,
        status=IncidentStatus.OPEN,
        confidence_score=50,
        anomalies=(
            _persisted_anomaly(AnomalyType.CATEGORY_SPIKE, "category", "payment_issue"),
            _persisted_anomaly(AnomalyType.COMPLAINT_SPIKE, "global", None),
        ),
    )

    incident = IncidentMapper.to_domain(persisted)

    assert incident.categories == (IssueCategory.PAYMENT_ISSUE,)


def test_derives_regions_from_region_scoped_anomalies():
    persisted = PersistedIncident(
        id=uuid.uuid4(),
        incident_key="INC-1",
        title="t",
        summary="s",
        severity=AnomalySeverity.HIGH,
        status=IncidentStatus.OPEN,
        confidence_score=50,
        anomalies=(_persisted_anomaly(AnomalyType.REGIONAL_SPIKE, "region", "South"),),
    )

    incident = IncidentMapper.to_domain(persisted)

    assert incident.regions == ("South",)


def test_derives_urgency_levels_from_urgency_scoped_anomalies():
    persisted = PersistedIncident(
        id=uuid.uuid4(),
        incident_key="INC-1",
        title="t",
        summary="s",
        severity=AnomalySeverity.HIGH,
        status=IncidentStatus.OPEN,
        confidence_score=50,
        anomalies=(_persisted_anomaly(AnomalyType.URGENCY_SPIKE, "urgency", "critical"),),
    )

    incident = IncidentMapper.to_domain(persisted)

    assert incident.urgency_levels == (UrgencyLabel.CRITICAL,)


def test_derives_anomaly_types_from_every_linked_anomaly():
    persisted = PersistedIncident(
        id=uuid.uuid4(),
        incident_key="INC-1",
        title="t",
        summary="s",
        severity=AnomalySeverity.HIGH,
        status=IncidentStatus.OPEN,
        confidence_score=50,
        anomalies=(
            _persisted_anomaly(AnomalyType.COMPLAINT_SPIKE, "global", None),
            _persisted_anomaly(AnomalyType.SENTIMENT_SHIFT, "global", None),
        ),
    )

    incident = IncidentMapper.to_domain(persisted)

    assert incident.anomaly_types == (AnomalyType.COMPLAINT_SPIKE, AnomalyType.SENTIMENT_SHIFT)
