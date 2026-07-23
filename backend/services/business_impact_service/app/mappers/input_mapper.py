from backend.services.business_impact_service.app.domain.anomaly_metrics import AnomalyMetrics
from backend.services.business_impact_service.app.domain.incident import Incident
from backend.services.business_impact_service.app.domain.root_cause_summary import RootCauseSummary
from backend.services.business_impact_service.app.domain.trend_metrics import TrendMetrics
from backend.services.business_impact_service.app.repositories.incident_read_repository import PersistedIncident
from backend.services.business_impact_service.app.repositories.root_cause_read_repository import PersistedRootCause
from backend.shared.constants.enums.anomaly import AnomalyType
from backend.shared.constants.enums.complaint import UrgencyLabel


class BusinessImpactInputMapper:
    """
    Business Impact Input Mapper

    Operational Purpose:
    Translates the read-only, persisted snapshots (`PersistedIncident`,
    `PersistedRootCause`) into the plain domain value objects the (frozen)
    Business Impact Engine expects (`Incident`, `RootCauseSummary`,
    `TrendMetrics`, `AnomalyMetrics`). The Engine must never receive a
    persisted or ORM object -- this mapper is the only place that boundary
    is crossed. Pure translation only -- no business/scoring logic.

    `entity_type`/`entity_value` on each linked anomaly encode the
    dimension it was raised for (Phase 5 Step 2's detectors), the same
    convention Root Cause Service's `IncidentMapper` already relies on: a
    "region"-scoped anomaly's `entity_value` is a raw region string, and an
    "urgency"-scoped anomaly's is an `UrgencyLabel` value.

    Known Limitation (Phase 7 Step 2):
    The current schema has no persisted concept of individual customers,
    SLA breaches, or a negative-sentiment ratio (verified against every
    anomaly detector in Phase 5 Step 2 and every ingestion/enrichment
    model). `affected_customer_count` is therefore approximated by the
    COMPLAINT_SPIKE anomaly's complaint count (the same proxy `TrendMetrics`
    already uses for volume); `sla_breach_count` and
    `negative_sentiment_ratio` deterministically default to 0 / 0.0 until a
    real data source exists. This is a deliberate, documented limitation,
    not a bug -- revisit when Phase 7 Step 3 or a later phase introduces the
    underlying data.
    """

    @staticmethod
    def to_incident(persisted: PersistedIncident) -> Incident:
        regions = tuple(
            anomaly.entity_value
            for anomaly in persisted.anomalies
            if anomaly.entity_type == "region" and anomaly.entity_value is not None
        )
        urgency_levels = tuple(
            UrgencyLabel(anomaly.entity_value)
            for anomaly in persisted.anomalies
            if anomaly.entity_type == "urgency" and anomaly.entity_value is not None
        )
        return Incident(
            incident_id=str(persisted.id),
            severity=persisted.severity,
            regions=regions,
            urgency_levels=urgency_levels,
        )

    @staticmethod
    def to_trend_metrics(persisted: PersistedIncident) -> TrendMetrics:
        volume_anomaly = next(
            (anomaly for anomaly in persisted.anomalies if anomaly.type == AnomalyType.COMPLAINT_SPIKE), None
        )
        if volume_anomaly is None:
            return TrendMetrics(current_volume=0, baseline_volume=0, percentage_change=0.0)
        return TrendMetrics(
            current_volume=int(volume_anomaly.current_value),
            baseline_volume=int(volume_anomaly.baseline_value),
            percentage_change=volume_anomaly.percentage_change or 0.0,
        )

    @staticmethod
    def to_anomaly_metrics(persisted: PersistedIncident) -> AnomalyMetrics:
        anomaly_types = tuple(anomaly.type for anomaly in persisted.anomalies)
        volume_anomaly = next(
            (anomaly for anomaly in persisted.anomalies if anomaly.type == AnomalyType.COMPLAINT_SPIKE), None
        )
        affected_customer_count = int(volume_anomaly.current_value) if volume_anomaly is not None else 0

        return AnomalyMetrics(
            anomaly_types=anomaly_types,
            severity=persisted.severity,
            affected_customer_count=affected_customer_count,
            sla_breach_count=0,
            negative_sentiment_ratio=0.0,
        )

    @staticmethod
    def to_root_cause_summary(persisted: PersistedRootCause) -> RootCauseSummary:
        return RootCauseSummary(
            cause=persisted.cause,
            confidence_score=persisted.confidence_score,
            confidence_level=persisted.confidence_level,
        )
