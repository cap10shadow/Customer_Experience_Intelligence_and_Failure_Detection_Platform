import uuid
from datetime import datetime
from typing import Sequence, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.ingestion_service.app.models.complaint import Complaint
from backend.shared.constants.enums.complaint import ComplaintStatus, SourceChannel
from backend.shared.constants.enums.enrichment import ProcessingStage
from backend.shared.constants.enums.business_impact import OperationalArea


class ComplaintRepository:
    """
    Complaint Repository

    Ownership:
    Owned by the Ingestion Service context.

    Operational Purpose:
    Responsible strictly for database persistence and retrieval of Complaint entities. 

    Architectural Boundaries:
    - This repository handles persistence ONLY.
    - Business reasoning, intelligence orchestration, and event triggering belong to the service layer.
    - API validation belongs to the FastAPI routers and Pydantic schemas.
    - Soft-deleted records are excluded by default unless explicitly requested.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_complaint(self, complaint: Complaint) -> Complaint:
        """Persists a new complaint."""
        self.session.add(complaint)
        await self.session.flush()
        return complaint

    async def get_by_id(self, complaint_id: uuid.UUID, include_deleted: bool = False) -> Complaint | None:
        """Retrieves a complaint by its internal UUID."""
        stmt = select(Complaint).where(Complaint.id == complaint_id)
        if not include_deleted:
            stmt = stmt.where(Complaint.is_deleted == False)
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_external_reference(self, ext_ref: str, include_deleted: bool = False) -> Complaint | None:
        """Retrieves a complaint by an external system reference."""
        stmt = select(Complaint).where(Complaint.external_reference_id == ext_ref)
        if not include_deleted:
            stmt = stmt.where(Complaint.is_deleted == False)
            
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def exists_by_source_record_hash(self, hash_val: str) -> bool:
        """
        Helper for future ingestion deduplication support.
        Checks if a payload hash already exists. Includes deleted records to prevent re-ingesting soft-deleted duplicates.
        """
        stmt = select(func.count(Complaint.id)).where(Complaint.source_record_hash == hash_val)
        result = await self.session.execute(stmt)
        count = result.scalar_one()
        return count > 0

    async def list_complaints(
        self,
        skip: int = 0,
        limit: int = 100,
        status: ComplaintStatus | None = None,
        stage: ProcessingStage | None = None,
        area: OperationalArea | None = None,
        channel: SourceChannel | None = None,
        region: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        include_deleted: bool = False,
    ) -> Sequence[Complaint]:
        """
        Lists complaints with optional operational filters and deterministic ordering.
        """
        stmt = select(Complaint)

        if not include_deleted:
            stmt = stmt.where(Complaint.is_deleted == False)

        if status is not None:
            stmt = stmt.where(Complaint.complaint_status == status)
            
        if stage is not None:
            stmt = stmt.where(Complaint.processing_stage == stage)
            
        if area is not None:
            stmt = stmt.where(Complaint.operational_area == area)
            
        if channel is not None:
            stmt = stmt.where(Complaint.source_channel == channel)
            
        if region is not None:
            stmt = stmt.where(Complaint.customer_region == region)
            
        if start_date is not None:
            stmt = stmt.where(Complaint.event_occurred_at >= start_date)
            
        if end_date is not None:
            stmt = stmt.where(Complaint.event_occurred_at <= end_date)

        # Deterministic ordering optimized for recent temporal analytics
        stmt = stmt.order_by(Complaint.event_occurred_at.desc().nullslast(), Complaint.id.desc())
        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_complaints(
        self,
        status: ComplaintStatus | None = None,
        stage: ProcessingStage | None = None,
        area: OperationalArea | None = None,
        channel: SourceChannel | None = None,
        region: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        include_deleted: bool = False,
    ) -> int:
        """Counts total complaints matching the given operational filters."""
        stmt = select(func.count(Complaint.id))

        if not include_deleted:
            stmt = stmt.where(Complaint.is_deleted == False)

        if status is not None:
            stmt = stmt.where(Complaint.complaint_status == status)
            
        if stage is not None:
            stmt = stmt.where(Complaint.processing_stage == stage)
            
        if area is not None:
            stmt = stmt.where(Complaint.operational_area == area)
            
        if channel is not None:
            stmt = stmt.where(Complaint.source_channel == channel)
            
        if region is not None:
            stmt = stmt.where(Complaint.customer_region == region)
            
        if start_date is not None:
            stmt = stmt.where(Complaint.event_occurred_at >= start_date)
            
        if end_date is not None:
            stmt = stmt.where(Complaint.event_occurred_at <= end_date)

        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def list_by_status(self, status: ComplaintStatus, limit: int = 100) -> Sequence[Complaint]:
        """Retrieves complaints by status, ordered by most recent."""
        return await self.list_complaints(status=status, limit=limit)

    async def list_by_region(self, region: str, limit: int = 100) -> Sequence[Complaint]:
        """Retrieves complaints by region, ordered by most recent."""
        return await self.list_complaints(region=region, limit=limit)

    async def list_recent_complaints(self, limit: int = 100) -> Sequence[Complaint]:
        """Retrieves recent complaints, ordered by occurred_at."""
        return await self.list_complaints(limit=limit)

    async def soft_delete_complaint(self, complaint_id: uuid.UUID) -> bool:
        """Marks a complaint as deleted without destroying the physical row."""
        complaint = await self.get_by_id(complaint_id)
        if complaint is None:
            return False
            
        complaint.is_deleted = True
        # Relying on outer transaction commit, just flush to context
        await self.session.flush()
        return True

    async def update_processing_stage(
        self, complaint_id: uuid.UUID, stage: ProcessingStage
    ) -> Complaint | None:
        """Advances or updates the intelligence processing stage."""
        complaint = await self.get_by_id(complaint_id)
        if complaint:
            complaint.processing_stage = stage
            await self.session.flush()
        return complaint

    async def update_complaint_status(
        self, complaint_id: uuid.UUID, status: ComplaintStatus
    ) -> Complaint | None:
        """Advances or updates the operational lifecycle status."""
        complaint = await self.get_by_id(complaint_id)
        if complaint:
            complaint.complaint_status = status
            await self.session.flush()
        return complaint
