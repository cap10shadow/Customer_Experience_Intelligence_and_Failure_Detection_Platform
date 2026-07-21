from backend.services.root_cause_service.app.domain.incident import Incident
from backend.services.root_cause_service.app.repositories.incident_read_repository import PersistedIncident
from backend.shared.constants.enums.complaint import IssueCategory, UrgencyLabel


class IncidentMapper:
    """
    Incident Mapper

    Operational Purpose:
    Translates a `PersistedIncident` (a plain, read-only snapshot of an
    Incident and its linked anomalies) into the domain `Incident` the
    (frozen) Root Cause Rule Engine expects. The Rule Engine must never
    receive a persisted or ORM object — this mapper is the only place that
    boundary is crossed.

    `entity_type`/`entity_value` on each linked anomaly encode the
    dimension it was raised for (Phase 5 Step 2's detectors): a
    "category"-scoped anomaly's `entity_value` is an `IssueCategory` value,
    a "region"-scoped anomaly's is a raw region string, and an
    "urgency"-scoped anomaly's is an `UrgencyLabel` value. This mapper is
    responsible for parsing those raw strings back into typed enums —
    formatting/translation only, no business rules.
    """

    @staticmethod
    def to_domain(persisted: PersistedIncident) -> Incident:
        categories = tuple(
            IssueCategory(anomaly.entity_value)
            for anomaly in persisted.anomalies
            if anomaly.entity_type == "category" and anomaly.entity_value is not None
        )
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
        anomaly_types = tuple(anomaly.type for anomaly in persisted.anomalies)

        return Incident(
            incident_key=persisted.incident_key,
            title=persisted.title,
            summary=persisted.summary,
            severity=persisted.severity,
            confidence_score=persisted.confidence_score,
            categories=categories,
            regions=regions,
            urgency_levels=urgency_levels,
            anomaly_types=anomaly_types,
        )
