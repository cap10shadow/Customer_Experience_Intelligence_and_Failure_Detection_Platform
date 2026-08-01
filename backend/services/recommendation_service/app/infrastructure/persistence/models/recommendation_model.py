import uuid
from datetime import datetime
from typing import Any, List

from sqlalchemy import DateTime, Enum, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.shared.database.base import Base


class RecommendationModel(Base):
    """
    Recommendation ORM Model (Infrastructure)

    Ownership:
    Owned by the Recommendation Service.

    Operational Purpose:
    Persists one Recommendation Aggregate (Phase 9 Step 1) as a single,
    append-only row. `recommendation_rationale`, `priority_rationale`, and
    `supporting_evidence` are stored as JSONB columns, per the frozen
    architecture's exact Recommendation table column list.

    Architectural Boundaries:
    - Lives entirely in Infrastructure; the Domain layer never imports this
      class. `RecommendationModelMapper` is the only component that
      translates between this ORM model and the Domain's
      `Recommendation`/`RecommendationRecord`.
    - `category`/`priority` reuse the (frozen) Phase 9 Step 1
      `RecommendationCategory`/`RecommendationPriority` Domain Enums as
      their own ORM column types -- the same precedent Root Cause's
      `RootCause` and Business Impact's `ImpactLevel`/`BusinessPriority`
      columns already established; reusing a service's own Domain enum as
      its own ORM column type is not a DATA-002 concern.
    - `incident_id` is a plain String column, not an ORM `ForeignKey` (see
      DATA-001/DATA-002): the Recommendation Service never imports the
      Anomaly Service's `Incident` ORM model.
    - `generation_id` is a plain UUID column, not an ORM `ForeignKey`
      either -- `RecommendationGenerationModel` is owned by this same
      service, but the frozen architecture treats grouping as a plain
      identifier relationship, and no join/relationship() is declared here
      (list_by_generation() filters by this column directly).
    - No update semantics: no `onupdate`, no mutable timestamp beyond
      `created_at` -- Recommendations are immutable and append-only. There
      is no repository method that would ever issue an UPDATE against this
      table.
    - No index on `category`/`priority`/`generation_id` individually: the
      frozen Index Strategy names only the primary key and the
      `(incident_id, generation_id)` composite index -- "add additional
      indexes ONLY if objectively required." `list_by_category()` and
      `list_by_priority()` therefore query without a dedicated index, as
      the frozen architecture specifies.

    Deviation (flagged, not silent):
    `action` is not in the frozen DATABASE MODEL's column list (neither
    relational nor JSONB), but `Recommendation.action` ("Recommended
    Action") is a required, non-empty Step 1 domain field enforced by the
    aggregate's own `__post_init__`. Omitting a column for it would mean
    every persisted Recommendation silently loses its actual recommended
    action -- the one thing a human downstream is meant to act on. Added
    as one relational `Text` column, matching this codebase's existing
    convention for plain-string explanatory fields (`RootCause.explanation`,
    `BusinessImpactAssessmentEntity.explanation`), not JSONB, since it is
    not listed under the frozen spec's JSONB column set either. See the
    Step 2 implementation report's Deviations section.
    """

    __tablename__ = "recommendations"

    recommendation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    incident_id: Mapped[str] = mapped_column(String(64), nullable=False)
    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    category: Mapped[RecommendationCategory] = mapped_column(Enum(RecommendationCategory), nullable=False)
    priority: Mapped[RecommendationPriority] = mapped_column(Enum(RecommendationPriority), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    # Not in the frozen column list -- see "Deviation" in this class's own
    # docstring. Required to avoid silently losing Recommendation.action.
    action: Mapped[str] = mapped_column(Text, nullable=False)

    recommendation_rationale: Mapped[str] = mapped_column(JSONB, nullable=False)
    priority_rationale: Mapped[str] = mapped_column(JSONB, nullable=False)
    supporting_evidence: Mapped[List[Any]] = mapped_column(JSONB, nullable=False)

    # `clock_timestamp()`, not `now()`: see EvaluationModel/RecommendationGenerationModel
    # for the identical, already-established rationale (ORDER BY created_at
    # DESC must stay deterministic for ties within one transaction).
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )

    __table_args__ = (Index("ix_recommendations_incident_id_generation_id", "incident_id", "generation_id"),)
