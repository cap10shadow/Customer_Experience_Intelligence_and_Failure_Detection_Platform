import uuid
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.anomaly_service.app.models.anomaly import ActiveAnomaly, AnomalyHistory
from backend.shared.constants.enums.anomaly import AnomalyStatus


class AnomalyRepository:
    """
    Anomaly Repository

    Ownership:
    Owned by the Anomaly Service context.

    Operational Purpose:
    Responsible strictly for database persistence and retrieval of
    ActiveAnomaly and AnomalyHistory entities. Contains no detection logic,
    no severity classification, and no explainability text generation —
    only data access.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Active anomalies
    # ------------------------------------------------------------------

    async def get_active_by_fingerprint(self, fingerprint: str) -> Optional[ActiveAnomaly]:
        """Retrieves an anomaly (ACTIVE or RESOLVED) by its deterministic fingerprint."""
        stmt = select(ActiveAnomaly).where(ActiveAnomaly.fingerprint == fingerprint)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, anomaly_id: uuid.UUID) -> Optional[ActiveAnomaly]:
        stmt = select(ActiveAnomaly).where(ActiveAnomaly.id == anomaly_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_active(self, anomaly: ActiveAnomaly) -> ActiveAnomaly:
        self.session.add(anomaly)
        await self.session.flush()
        return anomaly

    async def save(self, anomaly: ActiveAnomaly) -> ActiveAnomaly:
        """Flushes pending changes to an already-tracked ActiveAnomaly (the update path)."""
        await self.session.flush()
        return anomaly

    async def list_active(self, status: AnomalyStatus = AnomalyStatus.ACTIVE) -> Sequence[ActiveAnomaly]:
        stmt = (
            select(ActiveAnomaly)
            .where(ActiveAnomaly.status == status)
            .order_by(ActiveAnomaly.severity.desc(), ActiveAnomaly.last_seen_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    async def add_history_event(self, event: AnomalyHistory) -> AnomalyHistory:
        self.session.add(event)
        await self.session.flush()
        return event

    async def get_latest_run_timestamp(self) -> Optional[datetime]:
        """
        Returns the timestamp of the most recent detection run, derived as
        the latest of `active_anomalies.last_seen_at` (anomalies detected or
        reconfirmed) and `anomaly_history.event_timestamp` (covers a run
        that only resolved anomalies). None if no run has ever occurred.
        """
        last_seen = await self.session.execute(select(func.max(ActiveAnomaly.last_seen_at)))
        last_event = await self.session.execute(select(func.max(AnomalyHistory.event_timestamp)))

        candidates = [t for t in (last_seen.scalar_one_or_none(), last_event.scalar_one_or_none()) if t is not None]
        return max(candidates) if candidates else None

    async def list_history_at(self, timestamp: datetime) -> Sequence[AnomalyHistory]:
        """Returns every history event recorded at exactly the given run timestamp."""
        stmt = select(AnomalyHistory).where(AnomalyHistory.event_timestamp == timestamp)
        result = await self.session.execute(stmt)
        return result.scalars().all()
