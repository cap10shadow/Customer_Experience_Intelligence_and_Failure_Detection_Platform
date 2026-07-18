from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Index, String, Text
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
    customer_region: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    customer_segment: Mapped[Optional[CustomerSegment]] = mapped_column(Enum(CustomerSegment))
    customer_type: Mapped[Optional[CustomerType]] = mapped_column(Enum(CustomerType))

    # Operational Context
    product_category: Mapped[Optional[str]] = mapped_column(String(255))
    operational_area: Mapped[Optional[OperationalArea]] = mapped_column(Enum(OperationalArea), index=True)
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
    source_record_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)

    # Composite Indexes for Analytics Workloads
    __table_args__ = (
        Index("ix_complaints_status_occurred_at", "complaint_status", "event_occurred_at"),
        Index("ix_complaints_area_occurred_at", "operational_area", "event_occurred_at"),
    )
