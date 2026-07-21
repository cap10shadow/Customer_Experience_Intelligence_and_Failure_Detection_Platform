import uuid
from dataclasses import dataclass
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.root_cause_service.app.repositories.read_models import (
    active_anomalies_table,
    incident_anomalies_table,
    incidents_table,
)
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType
from backend.shared.constants.enums.incident import IncidentStatus


@dataclass(frozen=True)
class PersistedActiveAnomaly:
    """A read-only snapshot of one anomaly linked as evidence for an incident."""
    id: uuid.UUID
    type: AnomalyType
    entity_type: str
    entity_value: Optional[str]


@dataclass(frozen=True)
class PersistedIncident:
    """
    A read-only snapshot of an Incident plus its linked anomalies, exactly
    as persisted by the Anomaly Service. This is the sole input to
    `IncidentMapper.to_domain` — never an ORM object.
    """
    id: uuid.UUID
    incident_key: str
    title: str
    summary: str
    severity: AnomalySeverity
    status: IncidentStatus
    confidence_score: int
    anomalies: Tuple[PersistedActiveAnomaly, ...]


class IncidentReadRepository:
    """
    Incident Read Repository

    Ownership:
    Owned by the Root Cause Service context.

    Operational Purpose:
    Read-only access to `incidents`, `incident_anomalies`, and
    `active_anomalies` — tables owned by the Anomaly Service (see
    DATA-002). Never writes to these tables. Contains no root-cause
    business logic — only data access and assembly into plain,
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
            PersistedActiveAnomaly(id=row.id, type=row.type, entity_type=row.entity_type, entity_value=row.entity_value)
            for row in anomaly_rows
        )

        return PersistedIncident(
            id=incident_row.id,
            incident_key=incident_row.incident_key,
            title=incident_row.title,
            summary=incident_row.summary,
            severity=incident_row.severity,
            status=incident_row.status,
            confidence_score=incident_row.confidence_score,
            anomalies=anomalies,
        )
