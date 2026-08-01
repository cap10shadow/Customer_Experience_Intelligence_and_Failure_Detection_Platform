import uuid
from datetime import datetime

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
    """

    __tablename__ = "recommendation_generations"

    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(64), nullable=False)
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
