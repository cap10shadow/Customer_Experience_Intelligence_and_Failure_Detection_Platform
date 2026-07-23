import uuid

from backend.services.business_impact_service.app.mappers.input_mapper import BusinessImpactInputMapper
from backend.services.business_impact_service.app.repositories.incident_read_repository import (
    PersistedActiveAnomaly,
    PersistedIncident,
)
from backend.services.business_impact_service.app.repositories.root_cause_read_repository import PersistedRootCause
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType
from backend.shared.constants.enums.complaint import UrgencyLabel
from backend.shared.constants.enums.root_cause import RootCause


def _persisted_anomaly(type_, entity_type, entity_value, baseline_value=0.0, current_value=0.0, percentage_change=0.0):
    return PersistedActiveAnomaly(
        id=uuid.uuid4(),
        type=type_,
        entity_type=entity_type,
        entity_value=entity_value,
        baseline_value=baseline_value,
        current_value=current_value,
        percentage_change=percentage_change,
    )


def test_to_incident_maps_basic_fields():
    incident_id = uuid.uuid4()
    persisted = PersistedIncident(id=incident_id, severity=AnomalySeverity.CRITICAL, anomalies=())

    incident = BusinessImpactInputMapper.to_incident(persisted)

    assert incident.incident_id == str(incident_id)
    assert incident.severity == AnomalySeverity.CRITICAL
    assert incident.regions == ()
    assert incident.urgency_levels == ()


def test_to_incident_derives_regions_from_region_scoped_anomalies():
    persisted = PersistedIncident(
        id=uuid.uuid4(),
        severity=AnomalySeverity.HIGH,
        anomalies=(_persisted_anomaly(AnomalyType.REGIONAL_SPIKE, "region", "South"),),
    )

    incident = BusinessImpactInputMapper.to_incident(persisted)

    assert incident.regions == ("South",)


def test_to_incident_derives_urgency_levels_from_urgency_scoped_anomalies():
    persisted = PersistedIncident(
        id=uuid.uuid4(),
        severity=AnomalySeverity.HIGH,
        anomalies=(_persisted_anomaly(AnomalyType.URGENCY_SPIKE, "urgency", "critical"),),
    )

    incident = BusinessImpactInputMapper.to_incident(persisted)

    assert incident.urgency_levels == (UrgencyLabel.CRITICAL,)


def test_to_trend_metrics_defaults_to_zero_without_a_volume_anomaly():
    persisted = PersistedIncident(id=uuid.uuid4(), severity=AnomalySeverity.LOW, anomalies=())

    trend_metrics = BusinessImpactInputMapper.to_trend_metrics(persisted)

    assert trend_metrics.current_volume == 0
    assert trend_metrics.baseline_volume == 0
    assert trend_metrics.percentage_change == 0.0


def test_to_trend_metrics_reads_the_complaint_spike_anomaly_verbatim():
    persisted = PersistedIncident(
        id=uuid.uuid4(),
        severity=AnomalySeverity.HIGH,
        anomalies=(
            _persisted_anomaly(
                AnomalyType.COMPLAINT_SPIKE, "global", None, baseline_value=100.0, current_value=160.0, percentage_change=60.0
            ),
        ),
    )

    trend_metrics = BusinessImpactInputMapper.to_trend_metrics(persisted)

    assert trend_metrics.current_volume == 160
    assert trend_metrics.baseline_volume == 100
    assert trend_metrics.percentage_change == 60.0


def test_to_anomaly_metrics_defaults_unavailable_signals_to_zero():
    persisted = PersistedIncident(
        id=uuid.uuid4(),
        severity=AnomalySeverity.MEDIUM,
        anomalies=(_persisted_anomaly(AnomalyType.SENTIMENT_SHIFT, "global", None),),
    )

    anomaly_metrics = BusinessImpactInputMapper.to_anomaly_metrics(persisted)

    assert anomaly_metrics.anomaly_types == (AnomalyType.SENTIMENT_SHIFT,)
    assert anomaly_metrics.severity == AnomalySeverity.MEDIUM
    assert anomaly_metrics.affected_customer_count == 0
    assert anomaly_metrics.sla_breach_count == 0
    assert anomaly_metrics.negative_sentiment_ratio == 0.0


def test_to_anomaly_metrics_derives_affected_customer_count_from_complaint_spike():
    persisted = PersistedIncident(
        id=uuid.uuid4(),
        severity=AnomalySeverity.HIGH,
        anomalies=(
            _persisted_anomaly(AnomalyType.COMPLAINT_SPIKE, "global", None, current_value=250.0),
            _persisted_anomaly(AnomalyType.REGIONAL_SPIKE, "region", "South"),
        ),
    )

    anomaly_metrics = BusinessImpactInputMapper.to_anomaly_metrics(persisted)

    assert anomaly_metrics.affected_customer_count == 250
    assert anomaly_metrics.anomaly_types == (AnomalyType.COMPLAINT_SPIKE, AnomalyType.REGIONAL_SPIKE)


def test_to_root_cause_summary_maps_fields_verbatim():
    persisted_root_cause = PersistedRootCause(
        id=uuid.uuid4(),
        incident_id=uuid.uuid4(),
        cause=RootCause.SERVICE_OUTAGE,
        confidence_score=85,
        confidence_level="High",
    )

    summary = BusinessImpactInputMapper.to_root_cause_summary(persisted_root_cause)

    assert summary.cause == RootCause.SERVICE_OUTAGE
    assert summary.confidence_score == 85
    assert summary.confidence_level == "High"
