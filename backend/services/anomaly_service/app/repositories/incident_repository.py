import uuid
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.anomaly_service.app.models.anomaly import ActiveAnomaly
from backend.services.anomaly_service.app.models.incident import Incident, IncidentAnomaly
from backend.shared.constants.enums.incident import IncidentStatus


class IncidentRepository:
    """
    Incident Repository

    Ownership:
    Owned by the Anomaly Service context.

    Operational Purpose:
    Responsible strictly for database persistence and retrieval of Incident
    and IncidentAnomaly entities. Contains no correlation logic, no scoring,
    and no explanation text generation — only data access.

    Architectural Note:
    Joins ActiveAnomaly directly (both owned by this service) purely for
    reads — it never writes to `active_anomalies` or `anomaly_history`.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Incidents
    # ------------------------------------------------------------------

    async def create_incident(self, incident: Incident) -> Incident:
        self.session.add(incident)
        await self.session.flush()
        return incident

    async def save(self, incident: Incident) -> Incident:
        """Flushes pending changes to an already-tracked Incident (the update path)."""
        await self.session.flush()
        return incident

    async def get_by_id(self, incident_id: uuid.UUID) -> Optional[Incident]:
        stmt = select(Incident).where(Incident.id == incident_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_open(self) -> Sequence[Incident]:
        stmt = (
            select(Incident)
            .where(Incident.status == IncidentStatus.OPEN)
            .order_by(Incident.confidence_score.desc(), Incident.last_updated_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_open_incident_for_anomaly(self, active_anomaly_id: uuid.UUID) -> Optional[Incident]:
        """Returns the OPEN incident (if any) that a given anomaly is already linked to."""
        stmt = (
            select(Incident)
            .join(IncidentAnomaly, IncidentAnomaly.incident_id == Incident.id)
            .where(
                IncidentAnomaly.active_anomaly_id == active_anomaly_id,
                Incident.status == IncidentStatus.OPEN,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Incident <-> Anomaly links
    # ------------------------------------------------------------------

    async def is_anomaly_linked(self, incident_id: uuid.UUID, active_anomaly_id: uuid.UUID) -> bool:
        stmt = select(func.count(IncidentAnomaly.id)).where(
            IncidentAnomaly.incident_id == incident_id,
            IncidentAnomaly.active_anomaly_id == active_anomaly_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def link_anomaly(
        self, incident_id: uuid.UUID, active_anomaly_id: uuid.UUID, linked_at: datetime
    ) -> IncidentAnomaly:
        link = IncidentAnomaly(incident_id=incident_id, active_anomaly_id=active_anomaly_id, linked_at=linked_at)
        self.session.add(link)
        await self.session.flush()
        return link

    async def list_linked_anomalies(self, incident_id: uuid.UUID) -> Sequence[ActiveAnomaly]:
        stmt = (
            select(ActiveAnomaly)
            .join(IncidentAnomaly, IncidentAnomaly.active_anomaly_id == ActiveAnomaly.id)
            .where(IncidentAnomaly.incident_id == incident_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
