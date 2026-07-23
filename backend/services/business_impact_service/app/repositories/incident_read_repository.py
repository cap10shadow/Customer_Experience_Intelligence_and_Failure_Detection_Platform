import uuid
from dataclasses import dataclass
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.business_impact_service.app.repositories.read_models import (
    active_anomalies_table,
    incident_anomalies_table,
    incidents_table,
)
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType


@dataclass(frozen=True)
class PersistedActiveAnomaly:
    """A read-only snapshot of one anomaly linked as evidence for an incident."""
    id: uuid.UUID
    type: AnomalyType
    entity_type: str
    entity_value: Optional[str]
    baseline_value: float
    current_value: float
    percentage_change: Optional[float]


@dataclass(frozen=True)
class PersistedIncident:
    """
    A read-only snapshot of an Incident plus its linked anomalies, exactly
    as persisted by the Anomaly Service. This is the sole input the Input
    Mapper uses to build the Incident, TrendMetrics, and AnomalyMetrics
    domain value objects the (frozen) Business Impact Engine expects --
    never an ORM object.
    """
    id: uuid.UUID
    severity: AnomalySeverity
    anomalies: Tuple[PersistedActiveAnomaly, ...]


class IncidentReadRepository:
    """
    Incident Read Repository

    Ownership:
    Owned by the Business Impact Service context.

    Operational Purpose:
    Read-only access to `incidents`, `incident_anomalies`, and
    `active_anomalies` -- tables owned by the Anomaly Service (see
    DATA-002). Never writes to these tables. Contains no business-impact
    logic -- only data access and assembly into plain,
    persistence-independent snapshots.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, incident_id: uuid.UUID) -> Optional[PersistedIncident]:
        incident_stmt = select(incidents_table).where(incidents_table.c.id == incident_id)
        incident_row = (await self.session.execute(incident_stmt)).first()
        if incident_row is None:
            return None

        anomalies_stmt = (
            select(
                active_anomalies_table.c.id,
                active_anomalies_table.c.type,
                active_anomalies_table.c.entity_type,
                active_anomalies_table.c.entity_value,
                active_anomalies_table.c.baseline_value,
                active_anomalies_table.c.current_value,
                active_anomalies_table.c.percentage_change,
            )
            .select_from(
                active_anomalies_table.join(
                    incident_anomalies_table,
                    incident_anomalies_table.c.active_anomaly_id == active_anomalies_table.c.id,
                )
            )
            .where(incident_anomalies_table.c.incident_id == incident_id)
        )
        anomaly_rows = (await self.session.execute(anomalies_stmt)).all()

        anomalies = tuple(
            PersistedActiveAnomaly(
                id=row.id,
                type=row.type,
                entity_type=row.entity_type,
                entity_value=row.entity_value,
                baseline_value=row.baseline_value,
                current_value=row.current_value,
                percentage_change=row.percentage_change,
            )
            for row in anomaly_rows
        )

        return PersistedIncident(id=incident_row.id, severity=incident_row.severity, anomalies=anomalies)
