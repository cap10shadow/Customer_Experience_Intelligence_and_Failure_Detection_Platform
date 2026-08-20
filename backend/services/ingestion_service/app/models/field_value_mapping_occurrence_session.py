import uuid

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.database.base import Base, PrimaryKeyMixin, TimestampMixin


class FieldValueMappingOccurrenceSession(Base, PrimaryKeyMixin, TimestampMixin):
    """
    Idempotency ledger behind FieldValueMapping.occurrence_count.

    Ownership:
    Owned by the Ingestion Service.

    Problem this solves:
    classify_unique_values runs on every :analyze call, including
    deliberate re-analyzes of the same parsed rows (e.g. "refresh after
    approving a mapping"). Without this table, occurrence_count would
    double-count every re-analyze.

    Mechanism:
    The frontend generates one `analysis_session_id` per file parse and
    reuses it across every :analyze/:batch call for that same row set; a
    new upload always gets a new session id. One row here per
    (mapping_id, analysis_session_id) -- the unique constraint is the
    idempotency guarantee. FieldValueMappingRepository.record_occurrence()
    inserts a row here and bumps FieldValueMapping.occurrence_count in the
    same call ONLY if the (mapping_id, analysis_session_id) pair hasn't
    been recorded before; otherwise it's a no-op.
    """

    __tablename__ = "field_value_mapping_occurrence_sessions"

    mapping_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("field_value_mappings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "mapping_id", "analysis_session_id", name="uq_field_value_mapping_occurrence_sessions_mapping_session"
        ),
    )
