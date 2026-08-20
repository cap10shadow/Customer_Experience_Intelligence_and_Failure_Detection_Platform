import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.constants.enums.anomaly import AnomalyEventType, AnomalySeverity, AnomalyStatus, AnomalyType
from backend.shared.database.base import Base, PrimaryKeyMixin, TimestampMixin


class ActiveAnomaly(Base, PrimaryKeyMixin, TimestampMixin):
    """
    Active Anomaly Entity

    Ownership:
    Owned by the Anomaly Service.

    Operational Purpose:
    Represents the current state of a detected anomaly, identified by a
    deterministic fingerprint. One row per distinct (type, entity) dimension
    that is currently or was ever flagged by a detector.

    Explainability Philosophy:
    Every row carries the raw baseline/current values and percentage change
    that produced its severity, plus a human-readable explanation and the
    triggered rule description — no hidden calculations.
    """

    __tablename__ = "active_anomalies"

    # Dataset scoping (docs/DECISIONS.md AD-12) -- plain cross-service
    # columns (DATA-002: this service never imports ingestion_service's
    # ORM models), enforced at the DB level by the migration's raw
    # ForeignKeyConstraint. `dataset_id` determines isolation: every
    # query that lists/reconciles anomalies filters by it, so Dataset A's
    # anomalies can never appear while Dataset B is selected.
    # `last_analysis_version_id` is provenance only -- "as of which
    # analysis run was this anomaly's state last confirmed" -- and is
    # updated every time a run touches this row (create/reactivate/
    # update), never on a run that doesn't.
    dataset_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    last_analysis_version_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    # A fingerprint is only unique *within* a dataset -- two different
    # datasets can independently produce the identical fingerprint (e.g.
    # "complaint_spike:global:ALL") without colliding.
    fingerprint: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[AnomalyType] = mapped_column(Enum(AnomalyType), nullable=False, index=True)
    severity: Mapped[AnomalySeverity] = mapped_column(Enum(AnomalySeverity), nullable=False, index=True)

    # Dimension identity (what this anomaly is about).
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_value: Mapped[Optional[str]] = mapped_column(String(255))

    # Explainable metrics — the raw inputs behind the severity classification.
    baseline_value: Mapped[float] = mapped_column(Float, nullable=False)
    current_value: Mapped[float] = mapped_column(Float, nullable=False)
    percentage_change: Mapped[Optional[float]] = mapped_column(Float)
    triggered_rule: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    first_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    status: Mapped[AnomalyStatus] = mapped_column(
        Enum(AnomalyStatus), nullable=False, default=AnomalyStatus.ACTIVE, index=True
    )

    __table_args__ = (
        UniqueConstraint("fingerprint", "dataset_id", name="uq_active_anomalies_fingerprint_dataset_id"),
    )


class AnomalyHistory(Base, PrimaryKeyMixin, TimestampMixin):
    """
    Anomaly History Entity

    Ownership:
    Owned by the Anomaly Service.

    Operational Purpose:
    Append-only lifecycle log for an ActiveAnomaly. A row is written only
    when a meaningful state change occurs (creation, a severity change, or
    resolution) — routine re-confirmation of an unchanged anomaly on a given
    run does not produce a history row.

    Architectural Note:
    Unlike the Trend Engine's read-only cross-service tables, this entity
    references `active_anomalies` with a real ORM ForeignKey: both tables
    are owned by this same service, so none of the cross-service metadata
    coupling risk from DATA-002 applies here. No `relationship()` is
    declared since the repository queries both tables explicitly.
    """

    __tablename__ = "anomaly_history"

    active_anomaly_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("active_anomalies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # True version-addressable intelligence (AD-12 follow-up): which
    # DatasetVersion's analysis run wrote this history event. Combined
    # with `metrics_snapshot` (already a genuine point-in-time snapshot),
    # this makes "what did this anomaly look like as of Version N" a
    # real, queryable fact -- unlike `active_anomalies` itself (mutated
    # in place on every touching run), this table is append-only by
    # design, so no `dataset_version_id` history is ever overwritten. No
    # ORM ForeignKey to `dataset_versions` in the ingestion/gateway
    # sense is needed here beyond the raw FK the migration already
    # declares (DATA-001) -- this service never imports another
    # service's Dataset/DatasetVersion ORM model (DATA-002).
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    event_type: Mapped[AnomalyEventType] = mapped_column(Enum(AnomalyEventType), nullable=False, index=True)
    old_severity: Mapped[Optional[AnomalySeverity]] = mapped_column(Enum(AnomalySeverity))
    new_severity: Mapped[Optional[AnomalySeverity]] = mapped_column(Enum(AnomalySeverity))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    metrics_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
