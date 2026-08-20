import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.constants.enums.field_mapping import (
    FieldValueMappingConfidence,
    FieldValueMappingStatus,
    FieldValueMappingType,
)
from backend.shared.database.base import Base, PrimaryKeyMixin, TimestampMixin


class FieldValueMapping(Base, PrimaryKeyMixin, TimestampMixin):
    """
    A field-scoped, globally-reusable record of how one raw vocabulary
    value resolves to a canonical value.

    Ownership:
    Owned by the Ingestion Service.

    Scope:
    Global per (field_name, raw_value_normalized) -- not per dataset.
    `first_seen_dataset_id` is provenance only (which dataset first
    surfaced this value), never a lookup key, so an approved mapping is
    reused on every future upload regardless of dataset.

    Lifecycle:
    Only POST /field-mappings/{id}/approve and /bulk-approve may set
    `status=APPROVED` and write `target_value`. The classifier
    (mapping_service.classify_unique_values) only ever inserts PENDING
    rows or refreshes a PENDING row's `confidence`/`suggested_target_value`
    -- it never writes `status` or `target_value` under any input.

    occurrence_count:
    A derived, cached counter -- the source of truth is
    field_value_mapping_occurrence_sessions; this column is kept in sync
    exclusively via FieldValueMappingRepository.record_occurrence(), which
    is idempotent per (mapping_id, analysis_session_id) so re-analyzing
    the same upload never inflates it.
    """

    __tablename__ = "field_value_mappings"

    field_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    raw_value_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_value_original_example: Mapped[str] = mapped_column(String(255), nullable=False)

    target_value: Mapped[Optional[str]] = mapped_column(String(255))
    suggested_target_value: Mapped[Optional[str]] = mapped_column(String(255))

    confidence: Mapped[FieldValueMappingConfidence] = mapped_column(
        Enum(FieldValueMappingConfidence, name="fieldvaluemappingconfidence"), nullable=False
    )
    mapping_type: Mapped[Optional[FieldValueMappingType]] = mapped_column(
        Enum(FieldValueMappingType, name="fieldvaluemappingtype")
    )
    status: Mapped[FieldValueMappingStatus] = mapped_column(
        Enum(FieldValueMappingStatus, name="fieldvaluemappingstatus"),
        nullable=False,
        default=FieldValueMappingStatus.PENDING,
        index=True,
    )

    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    first_seen_dataset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("datasets.id", ondelete="SET NULL")
    )

    reviewed_by: Mapped[Optional[str]] = mapped_column(String(255))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint(
            "field_name", "raw_value_normalized", name="uq_field_value_mappings_field_raw"
        ),
        Index("ix_field_value_mappings_field_status", "field_name", "status"),
        Index("ix_field_value_mappings_field_confidence_status", "field_name", "confidence", "status"),
    )
