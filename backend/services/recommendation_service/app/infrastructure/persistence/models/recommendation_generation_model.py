import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.database.base import Base


class RecommendationGenerationModel(Base):
    """
    Recommendation Generation ORM Model (Infrastructure)

    Ownership:
    Owned by the Recommendation Service.

    Operational Purpose:
    Records that one Recommendation Decision Engine execution happened for
    one Incident -- grouping, immutable history, audit, and
    latest-generation lookup, exactly as the frozen architecture specifies.
    Contains no business logic and no reference to the Domain Engine.

    Architectural Boundaries:
    - `generation_id` is never generated here: per the frozen architecture,
      Generation identifiers are created in Step 3; Step 2's repository
      only ever persists a `generation_id` supplied by its caller. No
      `default=uuid.uuid4` on this column, deliberately.
    - `incident_id` is a plain String column, not an ORM `ForeignKey` (see
      DATA-001/DATA-002): the Recommendation Service never imports another
      service's `Incident` ORM model.
    - `created_at` uses `clock_timestamp()`, not `now()`, for the same
      reason `evaluations.created_at` does: `now()` is transaction-scoped
      and would return an identical value for every row inserted within
      one transaction, making "most recent generation" lookups
      non-deterministic for ties.
    - Not a Domain Aggregate: `RecommendationEngine`, the Rules, and
      `RecommendationConsolidator` never import or reference this class.
    - `event_id` (Step 3) is nullable and UNIQUE: the inbound
      `BusinessImpactCompleted` event identifier that triggered this
      execution. NULL is permitted (and repeatable -- PostgreSQL does not
      enforce uniqueness across NULLs) for generations persisted outside
      the event-driven lifecycle (e.g. every Step 2 test/usage). The
      UNIQUE constraint is the database-backed correctness guarantee
      behind `RecommendationLifecycleService`'s application-level
      idempotency check: it is what actually prevents two concurrent
      deliveries of the same event from ever producing two
      RecommendationGenerations. `event_id` is a distinct concept from
      `generation_id`: `event_id` identifies the inbound
      `BusinessImpactCompleted` event; `generation_id` identifies this
      Recommendation execution itself.
    """

    __tablename__ = "recommendation_generations"

    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    # Dataset scoping (docs/DECISIONS.md AD-12) -- see RecommendationModel's
    # identical field for the full rationale. Carried through unchanged
    # from the triggering `BusinessImpactCompleted` event's own
    # `dataset_id`.
    dataset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    # True version-addressable intelligence (AD-12 follow-up): which
    # DatasetVersion's analysis run produced this generation. Set once at
    # creation, never updated -- generations already accumulate one row
    # per analysis run rather than overwriting the previous one, so this
    # makes "the recommendation(s) generated for Version N" a real,
    # directly queryable fact.
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    incident_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )

    __table_args__ = (
        # Backs the frozen `GET /incidents/{incident_id}/recommendations/latest`
        # endpoint's query pattern ("find the most recent generation for
        # this incident") -- an objectively required index for a named,
        # in-scope query, not a speculative one.
        Index("ix_recommendation_generations_incident_id_created_at", "incident_id", "created_at"),
    )
