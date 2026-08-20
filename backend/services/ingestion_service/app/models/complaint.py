import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.constants.enums.business_impact import OperationalArea, ServiceType
from backend.shared.constants.enums.complaint import (
    ComplaintStatus,
    CustomerSegment,
    CustomerType,
    SourceChannel,
)
from backend.shared.constants.enums.enrichment import ProcessingStage
from backend.shared.database.base import Base, PrimaryKeyMixin, TimestampMixin


class Complaint(Base, PrimaryKeyMixin, TimestampMixin):
    """
    Core operational entity tracking customer complaints throughout their lifecycle.
    
    Ownership:
    Owned by the Ingestion Service, acting as the system of record.
    
    Operational Purpose:
    Centralizes all contextual, raw, and normalized complaint data to support downstream intelligence tracking.
    
    Enrichment Philosophy:
    Raw fields are preserved immutably, while operational context (normalized text, sentiment, etc.) 
    is iteratively hydrated by downstream NLP and anomaly pipelines.
    
    Lifecycle Role:
    Transitions from raw ingestion to resolution via 'processing_stage' and 'complaint_status'.
    """

    __tablename__ = "complaints"

    # Dataset ownership -- real, same-service ORM ForeignKey (Dataset is
    # owned by this same service). Every complaint belongs to exactly one
    # dataset; membership is permanent (never reassigned), which is what
    # makes "all complaints where dataset_id = X" a correct, cumulative
    # view of the dataset regardless of which version added any given row.
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # The specific DatasetVersion whose draft this complaint was ingested
    # into -- real provenance ("which version introduced this record"),
    # used to compute one version's new_record_count honestly and to
    # scope incremental NLP enrichment to only the records a given
    # finalize() call actually added, never a re-scan of the whole
    # dataset. Does NOT affect cumulative analysis scope -- that remains
    # "all complaints where dataset_id = X" regardless of this field.
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Identity Fields
    external_reference_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)

    # Raw Complaint Fields
    complaint_title: Mapped[Optional[str]] = mapped_column(String(255))
    complaint_text: Mapped[str] = mapped_column(Text, nullable=False)
    complaint_source: Mapped[Optional[str]] = mapped_column(String(255))
    source_channel: Mapped[Optional[SourceChannel]] = mapped_column(Enum(SourceChannel))

    # Normalized Fields
    normalized_title: Mapped[Optional[str]] = mapped_column(String(255))
    normalized_complaint_text: Mapped[Optional[str]] = mapped_column(Text)

    # Customer Context
    # `customer_region` holds the CANONICAL value once ingested through
    # :batch (see Ingestion Normalization & Mapping Layer plan) -- the
    # as-typed original is preserved separately in `raw_customer_region`
    # so downstream analytics (which reads `customer_region` under its
    # existing name, unchanged) automatically benefits from consolidated
    # vocabulary while the raw text stays auditable.
    customer_region: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    raw_customer_region: Mapped[Optional[str]] = mapped_column(String(100))
    customer_segment: Mapped[Optional[CustomerSegment]] = mapped_column(Enum(CustomerSegment))
    customer_type: Mapped[Optional[CustomerType]] = mapped_column(Enum(CustomerType))

    # Operational Context
    product_category: Mapped[Optional[str]] = mapped_column(String(255))
    # Same raw/canonical split as customer_region above.
    operational_area: Mapped[Optional[OperationalArea]] = mapped_column(Enum(OperationalArea), index=True)
    raw_operational_area: Mapped[Optional[str]] = mapped_column(String(100))
    service_type: Mapped[Optional[ServiceType]] = mapped_column(Enum(ServiceType))

    # Temporal Fields
    event_occurred_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)

    # Lifecycle & Soft Deletion Fields
    complaint_status: Mapped[ComplaintStatus] = mapped_column(
        Enum(ComplaintStatus), 
        default=ComplaintStatus.PENDING, 
        nullable=False, 
        index=True
    )
    processing_stage: Mapped[ProcessingStage] = mapped_column(
        Enum(ProcessingStage), 
        default=ProcessingStage.RAW_INGESTION, 
        nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Metadata Fields
    ingestion_source: Mapped[Optional[str]] = mapped_column(String(255))
    ingestion_batch_id: Mapped[Optional[str]] = mapped_column(String(255))
    # Unique, not just indexed -- the database-level backstop behind the
    # repository's own pre-check, closing a check-then-insert race under
    # concurrent/retried requests for the same record (two requests can
    # both pass an `exists` check before either commits; only a real
    # constraint stops both from landing). NULLs remain unconstrained
    # (Postgres never treats two NULLs as equal), so this cannot affect
    # any legacy row without a hash.
    source_record_hash: Mapped[Optional[str]] = mapped_column(String(64), unique=True)

    # Composite Indexes for Analytics Workloads
    __table_args__ = (
        Index("ix_complaints_status_occurred_at", "complaint_status", "event_occurred_at"),
        Index("ix_complaints_area_occurred_at", "operational_area", "event_occurred_at"),
        Index("ix_complaints_dataset_id_occurred_at", "dataset_id", "event_occurred_at"),
    )
