import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.constants.enums.dataset import DatasetVersionStatus
from backend.shared.database.base import Base, PrimaryKeyMixin, TimestampMixin


class Dataset(Base, PrimaryKeyMixin, TimestampMixin):
    """
    Dataset Entity

    Ownership:
    Owned by the Ingestion Service -- the natural owner, since a Dataset is
    fundamentally "a named, persistent grouping of ingested Complaint
    records," and Complaint is already this service's own entity.

    Operational Purpose:
    The top-level analytical workspace a user creates and returns to.
    Every Complaint belongs to exactly one Dataset (`Complaint.dataset_id`,
    a real same-service ORM ForeignKey). Every downstream service
    (nlp/anomaly/root_cause/business_impact/recommendation) references a
    Dataset's id or a DatasetVersion's id as a plain UUID column, exactly
    like every other cross-service reference in this platform (DATA-002)
    -- no ORM ForeignKey there, no shared metadata.
    """

    __tablename__ = "datasets"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)


class DatasetVersion(Base, PrimaryKeyMixin, TimestampMixin):
    """
    Dataset Version Entity

    Ownership:
    Owned by the Ingestion Service.

    Operational Purpose:
    A finalized snapshot marker for one dataset at one point in time, NOT
    a partition of which complaints belong to it -- a Dataset's complaint
    membership is cumulative by construction (Complaint.dataset_id alone;
    complaints are never removed), so "this version's data" always means
    "every complaint currently in this dataset." A DatasetVersion instead
    records: how many records existed when this version was finalized
    (`cumulative_record_count`), how many were newly added by this
    version specifically (`new_record_count`), and the real outcome of
    the analysis pipeline run for it (`status`, `failure_reason`).

    `version_number` is a plain, monotonically-increasing integer per
    dataset (1, 2, 3, ...) -- the "current version" is the highest
    `version_number` whose `status == READY`; a version still
    ingesting/processing/analyzing is real (visible in History) but never
    presented as the dataset's current state until it reaches READY.
    """

    __tablename__ = "dataset_versions"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[DatasetVersionStatus] = mapped_column(
        Enum(DatasetVersionStatus), nullable=False, default=DatasetVersionStatus.DRAFT, index=True
    )
    cumulative_record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysis_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    analysis_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("dataset_id", "version_number", name="uq_dataset_versions_dataset_id_version_number"),
    )
