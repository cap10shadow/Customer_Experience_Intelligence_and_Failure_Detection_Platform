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

    async def get(self, root_cause_id: uuid.UUID, dataset_id: Optional[uuid.UUID] = None) -> Optional[RootCause]:
        """
        By-id lookup, optionally scoped to `dataset_id`. The public
        `GET /root-causes/{id}` route always supplies `dataset_id` (see
        `api/root_causes.py`), so a caller cannot retrieve a RootCause
        belonging to a dataset it did not ask for through that route — a
        `root_cause_id` that exists but belongs to a different dataset
        returns None there, identical to a genuinely missing id. The
        lifecycle transitions (`confirm`/`reject`/`refresh`) resolve a
        RootCause by id alone, unchanged — they operate on an id an
        operator already has in hand from a dataset-scoped read, not on
        caller-suppliable dataset context.
        """
        stmt = select(RootCause).where(RootCause.id == root_cause_id)
        if dataset_id is not None:
            stmt = stmt.where(RootCause.dataset_id == dataset_id)
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

    async def list(self, dataset_id: Optional[uuid.UUID] = None) -> Sequence[RootCause]:
        stmt = select(RootCause).order_by(RootCause.created_at.desc())
        if dataset_id is not None:
            stmt = stmt.where(RootCause.dataset_id == dataset_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
