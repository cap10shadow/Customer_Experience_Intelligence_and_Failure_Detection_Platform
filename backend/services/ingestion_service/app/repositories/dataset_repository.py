import uuid
from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.ingestion_service.app.models.complaint import Complaint
from backend.services.ingestion_service.app.models.dataset import Dataset, DatasetVersion
from backend.shared.constants.enums.dataset import DatasetVersionStatus


class DatasetRepository:
    """
    Dataset Repository

    Ownership:
    Owned by the Ingestion Service context.

    Operational Purpose:
    Persistence for Dataset and DatasetVersion entities, plus the
    dataset-scoped complaint-counting queries the version lifecycle needs
    (record counts are always a real COUNT at the moment they're read or
    snapshotted, never a maintained/cached counter that could drift).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Dataset
    # ------------------------------------------------------------------

    async def create_dataset(self, dataset: Dataset) -> Dataset:
        self.session.add(dataset)
        await self.session.flush()
        return dataset

    async def get_dataset(self, dataset_id: uuid.UUID, include_deleted: bool = False) -> Optional[Dataset]:
        stmt = select(Dataset).where(Dataset.id == dataset_id)
        if not include_deleted:
            stmt = stmt.where(Dataset.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_datasets(self, include_deleted: bool = False) -> Sequence[Dataset]:
        stmt = select(Dataset)
        if not include_deleted:
            stmt = stmt.where(Dataset.is_deleted.is_(False))
        stmt = stmt.order_by(Dataset.inserted_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def archive_dataset(self, dataset_id: uuid.UUID) -> Optional[Dataset]:
        """
        Soft-deletes a Dataset (is_deleted = True) -- never a hard DELETE.
        DatasetVersions, Complaints, and every cross-service intelligence
        entity (anomalies, incidents, root causes, business impact,
        recommendations) that reference this dataset's or its versions'
        ids are left completely untouched: nothing here removes a row or
        breaks a foreign key. `get_dataset`/`list_datasets` already
        exclude is_deleted datasets by default, so archiving alone is
        what makes the dataset disappear from listings and become
        unselectable -- no other state change is needed.
        """
        dataset = await self.get_dataset(dataset_id)
        if dataset is None:
            return None
        dataset.is_deleted = True
        await self.session.flush()
        return dataset

    # ------------------------------------------------------------------
    # DatasetVersion
    # ------------------------------------------------------------------

    async def create_dataset_version(self, version: DatasetVersion) -> DatasetVersion:
        self.session.add(version)
        await self.session.flush()
        return version

    async def get_dataset_version(self, version_id: uuid.UUID) -> Optional[DatasetVersion]:
        stmt = select(DatasetVersion).where(DatasetVersion.id == version_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_dataset_versions(self, dataset_id: uuid.UUID) -> Sequence[DatasetVersion]:
        stmt = (
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.version_number.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_draft_version(self, dataset_id: uuid.UUID) -> Optional[DatasetVersion]:
        """The one DatasetVersion per dataset currently open to receive new complaints."""
        stmt = select(DatasetVersion).where(
            DatasetVersion.dataset_id == dataset_id, DatasetVersion.status == DatasetVersionStatus.DRAFT
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_current_ready_version(self, dataset_id: uuid.UUID) -> Optional[DatasetVersion]:
        """The highest-numbered version whose analysis genuinely completed -- what Dashboard/Analytics present as 'current'."""
        stmt = (
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset_id, DatasetVersion.status == DatasetVersionStatus.READY)
            .order_by(DatasetVersion.version_number.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_version(self, dataset_id: uuid.UUID) -> Optional[DatasetVersion]:
        """The highest-numbered version regardless of status -- used to show 'new data processing' state."""
        stmt = (
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.version_number.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_version(self, version: DatasetVersion) -> DatasetVersion:
        await self.session.flush()
        return version

    # ------------------------------------------------------------------
    # Dataset-scoped complaint counts
    # ------------------------------------------------------------------

    async def count_complaints_in_dataset(self, dataset_id: uuid.UUID) -> int:
        stmt = select(func.count(Complaint.id)).where(
            Complaint.dataset_id == dataset_id, Complaint.is_deleted.is_(False)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_complaints_in_version(self, dataset_version_id: uuid.UUID) -> int:
        stmt = select(func.count(Complaint.id)).where(
            Complaint.dataset_version_id == dataset_version_id, Complaint.is_deleted.is_(False)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def list_complaint_ids_in_version(self, dataset_version_id: uuid.UUID) -> Sequence[uuid.UUID]:
        """The complaints a specific finalize() call actually added -- what needs NLP enrichment for this version's analysis run."""
        stmt = select(Complaint.id).where(
            Complaint.dataset_version_id == dataset_version_id, Complaint.is_deleted.is_(False)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
