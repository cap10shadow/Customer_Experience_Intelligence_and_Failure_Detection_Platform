import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.business_impact_service.app.domain.business_priority import BusinessPriority
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.models.business_impact_assessment import (
    BusinessImpactAssessmentEntity,
)


class BusinessImpactRepository:
    """
    BusinessImpactAssessment Repository

    Ownership:
    Owned by the Business Impact Service context.

    Operational Purpose:
    Responsible strictly for database persistence and retrieval of
    BusinessImpactAssessment entities. Contains no business logic, no
    scoring, and no engine execution -- only data access.

    Assessments are immutable once created (see BusinessImpactAssessmentEntity
    docstring) -- this repository exposes no update operation.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, assessment: BusinessImpactAssessmentEntity) -> BusinessImpactAssessmentEntity:
        """Persists a new BusinessImpactAssessment record and flushes to the session."""
        self.session.add(assessment)
        await self.session.flush()
        return assessment

    async def get(
        self, assessment_id: uuid.UUID, dataset_id: Optional[uuid.UUID] = None
    ) -> Optional[BusinessImpactAssessmentEntity]:
        """
        By-id lookup, optionally scoped to `dataset_id`. The public
        `GET /business-impact/{id}` route always supplies `dataset_id`
        (see `api/business_impact.py`), so a caller cannot retrieve an
        assessment belonging to a dataset it did not ask for through
        that route — an `assessment_id` that exists but belongs to a
        different dataset returns None there, identical to a genuinely
        missing id.
        """
        stmt = select(BusinessImpactAssessmentEntity).where(
            BusinessImpactAssessmentEntity.assessment_id == assessment_id
        )
        if dataset_id is not None:
            stmt = stmt.where(BusinessImpactAssessmentEntity.dataset_id == dataset_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        severity: Optional[ImpactLevel] = None,
        priority: Optional[BusinessPriority] = None,
        incident_id: Optional[uuid.UUID] = None,
        dataset_id: Optional[uuid.UUID] = None,
        dataset_version_id: Optional[uuid.UUID] = None,
    ) -> Sequence[BusinessImpactAssessmentEntity]:
        """Returns persisted assessments, optionally filtered by severity, priority, incident, dataset, and/or dataset version."""
        stmt = select(BusinessImpactAssessmentEntity)
        if severity is not None:
            stmt = stmt.where(BusinessImpactAssessmentEntity.overall_severity == severity)
        if priority is not None:
            stmt = stmt.where(BusinessImpactAssessmentEntity.business_priority == priority)
        if incident_id is not None:
            stmt = stmt.where(BusinessImpactAssessmentEntity.incident_id == incident_id)
        if dataset_id is not None:
            stmt = stmt.where(BusinessImpactAssessmentEntity.dataset_id == dataset_id)
        if dataset_version_id is not None:
            stmt = stmt.where(BusinessImpactAssessmentEntity.dataset_version_id == dataset_version_id)
        stmt = stmt.order_by(BusinessImpactAssessmentEntity.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()
