import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.services.business_impact_service.app.domain.business_priority import BusinessPriority
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.shared.constants.enums.business_impact_assessment import BusinessImpactAssessmentStatus
from backend.shared.database.base import Base


class BusinessImpactAssessmentEntity(Base):
    """
    Business Impact Assessment Entity

    Ownership:
    Owned by the Business Impact Service.

    Operational Purpose:
    Persists a single, immutable Business Impact Analysis Engine run
    (Phase 7 Step 1) for one Incident and its identified RootCause. Unlike
    RootCause (exactly one per Incident), an Incident may accumulate
    multiple BusinessImpactAssessment rows over time as trend/anomaly data
    evolves -- no unique constraint on `incident_id` -- consistent with the
    platform's "preserve historical intelligence evolution over time"
    database philosophy (ARCHITECTURE.md).

    Architectural Boundaries:
    - `incident_id` and `root_cause_id` are plain UUID columns, not ORM
      `ForeignKey`s: the Business Impact Service does not import the
      Anomaly Service's `Incident` ORM model or the Root Cause Service's
      `RootCause` ORM model (see DATA-002), so neither table is registered
      in this service's own metadata. Referential integrity to
      `incidents.id` and `root_causes.id` is enforced at the database level
      by the Alembic migration's raw `ForeignKeyConstraint`s instead (see
      DATA-001).
    - `financial`/`customer`/`operational`/`sla`/`reputation` and
      `overall_severity` reuse the (frozen) Phase 7 Step 1 `ImpactLevel`
      domain enum; `business_priority` reuses the (frozen) `BusinessPriority`
      domain enum. Reusing a service's own domain enums as its own ORM
      column types is not a DATA-002 concern -- that restriction is about
      importing *another service's* ORM/domain classes.

    Explainability Philosophy:
    Every field here is a direct, unmodified copy of the
    BusinessImpactAssessment the (frozen) Engine returned -- no additional
    calculation happens at the persistence layer.

    Forward Compatibility:
    `status` and `updated_at` exist for Phase 7 Step 3's lifecycle
    management. Step 2 assigns `status=ACTIVE` on creation and never
    transitions or updates it -- no lifecycle behavior is introduced here.
    """

    __tablename__ = "business_impact_assessments"

    assessment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    root_cause_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    financial: Mapped[ImpactLevel] = mapped_column(Enum(ImpactLevel), nullable=False)
    customer: Mapped[ImpactLevel] = mapped_column(Enum(ImpactLevel), nullable=False)
    operational: Mapped[ImpactLevel] = mapped_column(Enum(ImpactLevel), nullable=False)
    sla: Mapped[ImpactLevel] = mapped_column(Enum(ImpactLevel), nullable=False)
    reputation: Mapped[ImpactLevel] = mapped_column(Enum(ImpactLevel), nullable=False)

    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_severity: Mapped[ImpactLevel] = mapped_column(Enum(ImpactLevel), nullable=False, index=True)
    business_priority: Mapped[BusinessPriority] = mapped_column(Enum(BusinessPriority), nullable=False, index=True)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_affected_customers: Mapped[int] = mapped_column(Integer, nullable=False)

    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[BusinessImpactAssessmentStatus] = mapped_column(
        Enum(BusinessImpactAssessmentStatus),
        nullable=False,
        default=BusinessImpactAssessmentStatus.ACTIVE,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Deliberately no `onupdate=func.now()` -- same MissingGreenlet hazard
    # documented on RootCause.updated_at. Not touched at all during Step 2
    # (no update endpoint); reserved for Phase 7 Step 3.
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
