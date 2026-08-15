import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.services.recommendation_service.app.domain.recommendation_decision import RecommendationDecision
from backend.shared.database.base import Base


class RecommendationDecisionHistoryModel(Base):
    """
    Recommendation Decision History ORM Model (Infrastructure)

    Ownership:
    Owned by the Recommendation Service.

    Operational Purpose:
    Append-only record of every successful `PATCH .../decision` call
    against one Recommendation -- "what did this Recommendation's
    decision look like at each point in time" (Phase 13 Batch 5, AD-3,
    docs/architecture/phase-13/PHASE_13_ARCHITECTURE.md §14/§15). The
    existing `recommendations.decision`/`decision_note`/`decided_at`
    columns keep their current unconditional-overwrite semantics for
    fast current-state reads, exactly as REC-003 designed; this table
    is the append-only complement, never a replacement for that
    current-state read path.

    Architectural Boundaries:
    - `recommendation_id` is a real ORM `ForeignKey` to
      `recommendations.recommendation_id`: both tables are owned by this
      same service, matching the `CopilotMessage` ->
      `copilot_conversations` precedent (a real, same-service FK is
      appropriate; only cross-service references use a raw, ORM-free
      Alembic constraint per DATA-001/DATA-002). AD-3 itself calls this
      FK "recommended for integrity", not required.
    - `actor_id` is a plain nullable UUID column, *not* an ORM
      `ForeignKey` -- it references `gateway_service`'s `users.id`,
      a cross-service table this service's own SQLAlchemy metadata must
      never register (DATA-001/DATA-002). Referential integrity is
      enforced by a raw Alembic `ForeignKeyConstraint` only (see the
      migration). Populated exclusively from the Gateway-attested
      principal header, never from client-supplied request data --
      nullable so a pre-Phase-13 or unattributed decision can still be
      recorded honestly, without a fabricated actor.
    - No `updated_at`, no update semantics of any kind: this table is
      genuinely append-only. No repository method issues an UPDATE or
      DELETE against it.
    - `created_at` uses `clock_timestamp()`, not `now()`, matching
      `recommendations.created_at`/`recommendation_generations.created_at`'s
      own established rationale -- `now()` is transaction-scoped and
      would return an identical value for every row inserted within one
      transaction, making history ordering non-deterministic for ties.
    """

    __tablename__ = "recommendation_decision_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recommendations.recommendation_id"), nullable=False
    )
    decision: Mapped[RecommendationDecision] = mapped_column(Enum(RecommendationDecision), nullable=False)
    decision_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )

    __table_args__ = (Index("ix_recommendation_decision_history_recommendation_id", "recommendation_id"),)
