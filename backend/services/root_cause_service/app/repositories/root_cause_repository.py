import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.root_cause_service.app.models.root_cause import RootCause


class RootCauseRepository:
    """
    RootCause Repository

    Ownership:
    Owned by the Root Cause Service context.

    Operational Purpose:
    Responsible strictly for database persistence and retrieval of
    RootCause entities. Contains no business logic, no scoring, and no
    rule execution — only data access.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, root_cause: RootCause) -> RootCause:
        """Persists a new RootCause record and flushes to the session."""
        self.session.add(root_cause)
        await self.session.flush()
        return root_cause

    async def update(self, root_cause: RootCause) -> RootCause:
        """Flushes pending changes to an already-tracked RootCause (the update path)."""
        await self.session.flush()
        return root_cause

    async def get(self, root_cause_id: uuid.UUID) -> Optional[RootCause]:
        stmt = select(RootCause).where(RootCause.id == root_cause_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_incident(self, incident_id: uuid.UUID) -> Optional[RootCause]:
        """
        Retrieves the RootCause linked to a given incident.

        Returns None if the incident has not been analyzed yet. Because
        `incident_id` carries a unique constraint, at most one record can
        exist per incident.
        """
        stmt = select(RootCause).where(RootCause.incident_id == incident_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self) -> Sequence[RootCause]:
        stmt = select(RootCause).order_by(RootCause.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()
