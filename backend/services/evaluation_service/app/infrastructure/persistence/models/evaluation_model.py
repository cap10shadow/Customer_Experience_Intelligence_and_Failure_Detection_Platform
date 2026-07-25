import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, Index, String, desc, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.database.base import Base


class EvaluationModel(Base):
    """
    Evaluation ORM Model (Infrastructure)

    Ownership:
    Owned by the Evaluation Service.

    Operational Purpose:
    Persists the Evaluation Aggregate as a single, append-only row.
    ValidationSummary, QualityAssessment, ExplainabilityAssessment,
    ConfidenceSummary, and EvaluationMetadata are stored as JSONB columns,
    never normalized into separate tables (per the approved architecture)
    -- they are intrinsic parts of one Evaluation, never independently
    queried, joined, or mutated.

    Architectural Boundaries:
    - Lives entirely in Infrastructure; the Domain layer never imports this
      class. `EvaluationModelMapper` is the only component that translates
      between this ORM model and the Domain's `Evaluation`/`EvaluationRecord`.
    - No update semantics: no `onupdate`, no mutable timestamp beyond
      `created_at` -- Evaluations are immutable and append-only. There is
      no repository method that would ever issue an UPDATE against this
      table.
    - `incident_id` is a plain String column, not an ORM `ForeignKey` (see
      DATA-001/DATA-002): the Evaluation Service never imports the Anomaly
      Service's `Incident` ORM model. It is deliberately typed as `String`
      rather than a native UUID column because the Domain-layer
      `Evaluation.incident_id` is itself a plain `str` (Phase 8 Step 1,
      frozen) with no UUID-format guarantee enforced at that layer.
    - `root_cause_id` / `business_impact_id` are nullable and, as of Step 2,
      always NULL -- there is no upstream event data yet to populate them
      from (see `EvaluationRecord`'s docstring). `previous_evaluation_id`
      is a plain UUID column (not a `ForeignKey`, same DATA-001/DATA-002
      reasoning) referencing another row's `evaluation_id`.
    """

    __tablename__ = "evaluations"

    evaluation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    incident_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    root_cause_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    business_impact_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    evaluation_version: Mapped[str] = mapped_column(String(20), nullable=False)
    previous_evaluation_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    validation_summary: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    quality_assessment: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    explainability_assessment: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    confidence_summary: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Python attribute deliberately not named `metadata`: that name is
    # reserved by SQLAlchemy's DeclarativeBase (`Base.metadata`). The
    # actual database column is still named `metadata`, per the approved
    # architecture's exact JSONB column list.
    evaluation_metadata: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False)

    # `clock_timestamp()`, not `now()`: PostgreSQL's `now()` is
    # transaction-scoped and returns the SAME value for every statement
    # within one transaction, so two `save()` calls sharing a transaction
    # (or simply landing in the same request session) would get identical
    # `created_at` values, making `ORDER BY created_at DESC` (get_latest,
    # list_by_incident) non-deterministic for ties. `clock_timestamp()` is
    # evaluated per-statement, giving every row a genuinely distinct value.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )

    __table_args__ = (
        Index("ix_evaluations_incident_id_evaluation_version", "incident_id", desc("evaluation_version")),
    )
