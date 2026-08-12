import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.business_impact_service.app.repositories.read_models import root_causes_table
from backend.shared.constants.enums.root_cause import RootCause as RootCauseEnum


@dataclass(frozen=True)
class PersistedRootCause:
    """
    A read-only snapshot of a RootCause record, exactly as persisted by the
    Root Cause Service. This is the sole input the Input Mapper uses to
    build the RootCauseSummary domain value object the (frozen) Business
    Impact Engine expects -- never an ORM object.

    `evidence`/`explanation` (Part 6) are NOT read by the Engine or
    `BusinessImpactInputMapper.to_root_cause_summary` -- they exist only so
    `BusinessImpactEventPublisher` can populate evaluation_service's
    already-frozen `root_cause_explanation`/`root_cause_evidence_count`
    event fields. Defaulted (rather than required) so every existing
    call site that only needs the Engine's own three fields keeps working
    unchanged.
    """
    id: uuid.UUID
    incident_id: uuid.UUID
    cause: RootCauseEnum
    confidence_score: int
    confidence_level: str
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    explanation: str = ""


class RootCauseReadRepository:
    """
    RootCause Read Repository

    Ownership:
    Owned by the Business Impact Service context.

    Operational Purpose:
    Read-only access to `root_causes` -- a table owned by the Root Cause
    Service (see DATA-002). Never writes to this table. Contains no
    business-impact logic -- only data access and assembly into a plain,
    persistence-independent snapshot.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_incident(self, incident_id: uuid.UUID) -> Optional[PersistedRootCause]:
        """
        Retrieves the RootCause linked to a given incident.

        Returns None if the incident has not been analyzed by the Root
        Cause Service yet.
        """
        stmt = select(root_causes_table).where(root_causes_table.c.incident_id == incident_id)
        row = (await self.session.execute(stmt)).first()
        if row is None:
            return None
        return PersistedRootCause(
            id=row.id,
            incident_id=row.incident_id,
            cause=row.cause,
            confidence_score=row.confidence_score,
            confidence_level=row.confidence_level,
            evidence=row.evidence or [],
            explanation=row.explanation or "",
        )
