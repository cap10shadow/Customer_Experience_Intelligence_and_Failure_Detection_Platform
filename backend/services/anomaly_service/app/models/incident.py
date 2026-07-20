import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.constants.enums.anomaly import AnomalySeverity
from backend.shared.constants.enums.incident import IncidentStatus
from backend.shared.database.base import Base, PrimaryKeyMixin, TimestampMixin


class Incident(Base, PrimaryKeyMixin, TimestampMixin):
    """
    Incident Entity

    Ownership:
    Owned by the Anomaly Service.

    Operational Purpose:
    Groups one or more related active anomalies into a single operational
    problem, as determined by the deterministic Correlation Engine. This is
    the primary object future phases (Root Cause Analysis, Business Impact,
    Recommendations) will operate on.

    Explainability Philosophy:
    `confidence_score` and `summary` are derived entirely from the
    correlation rules' outputs — no hidden calculations. Anomalies remain
    immutable evidence: this entity only records relationships to them via
    `incident_anomalies`, never modifying `active_anomalies` or
    `anomaly_history`.
    """

    __tablename__ = "incidents"

    incident_key: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[AnomalySeverity] = mapped_column(Enum(AnomalySeverity), nullable=False, index=True)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus), nullable=False, default=IncidentStatus.OPEN, index=True
    )
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class IncidentAnomaly(Base, PrimaryKeyMixin, TimestampMixin):
    """
    Incident-Anomaly Link Entity

    Ownership:
    Owned by the Anomaly Service.

    Operational Purpose:
    Records that a given active anomaly is evidence for a given incident.
    Purely a relationship table — no correlation logic lives here. Both
    `incidents` and `active_anomalies` are owned by this same service, so
    real ORM ForeignKeys are used (see DATA-002, which only restricts
    cross-service references).
    """

    __tablename__ = "incident_anomalies"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    active_anomaly_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("active_anomalies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("incident_id", "active_anomaly_id", name="uq_incident_anomalies_incident_active_anomaly"),
    )
