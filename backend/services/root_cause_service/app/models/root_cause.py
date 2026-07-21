import uuid
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.constants.enums.root_cause import RootCause as RootCauseEnum
from backend.shared.constants.enums.root_cause import RootCauseStatus
from backend.shared.database.base import Base, PrimaryKeyMixin


class RootCause(Base, PrimaryKeyMixin):
    """
    Root Cause Entity

    Ownership:
    Owned by the Root Cause Service.

    Operational Purpose:
    Persists the outcome of a single deterministic Root Cause Rule Engine
    run (Phase 6 Step 1) for one Incident. Exactly one RootCause per
    Incident — enforced by the unique constraint on `incident_id`.

    Architectural Boundaries:
    - `incident_id` is a plain UUID column, not an ORM `ForeignKey`: the
      Root Cause Service does not import the Anomaly Service's `Incident`
      ORM model (see DATA-002), so that table is never registered in this
      service's own metadata. Referential integrity to `incidents.id` is
      enforced at the database level by the Alembic migration's raw
      `ForeignKeyConstraint` instead (see DATA-001).
    - `evidence` is stored as JSONB, intentionally not normalized into
      relational tables — it mirrors the Evidence value objects the
      (frozen) Rule Engine produces, one-for-one.

    Explainability Philosophy:
    Every field here is a direct, unmodified copy of the RootCauseCandidate
    the Rule Engine returned — no additional calculation happens at the
    persistence layer.
    """

    __tablename__ = "root_causes"

    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    cause: Mapped[RootCauseEnum] = mapped_column(Enum(RootCauseEnum), nullable=False, index=True)
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(20), nullable=False)
    evidence: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[RootCauseStatus] = mapped_column(
        Enum(RootCauseStatus), nullable=False, default=RootCauseStatus.IDENTIFIED, index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
