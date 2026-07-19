import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ARRAY, DateTime, Enum, Float, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.constants.enums.complaint import IssueCategory, SentimentLabel, UrgencyLabel
from backend.shared.database.base import Base, PrimaryKeyMixin, TimestampMixin


class ComplaintEnrichment(Base, PrimaryKeyMixin, TimestampMixin):
    """
    NLP Enrichment Entity

    Ownership:
    Owned by the NLP Service.

    Operational Purpose:
    Stores the analytical and intelligence outputs derived from processing
    the raw text of a Complaint. Separating this from the core Complaint
    entity ensures the raw operational datastore remains isolated from
    frequent AI inference updates.

    Explainability Philosophy:
    - Operational Explainability: Every enrichment output is tied back directly to the inference latency and source.
    - Traceability: Tracks exact model versions and names to allow auditing of classification drift over time.
    - Reproducibility: Stores the deterministic confidence score of the prediction.
    - Intelligence Outputs: Categorization, sentiment, and keyword extraction to support downstream anomaly detection.
    """

    __tablename__ = "complaint_enrichments"

    # Identity & Linkage
    # Deliberately not an ORM-level ForeignKey: the NLP service does not import
    # or map the Complaint entity, so "complaints" is never registered in this
    # process's metadata and a ForeignKey object would fail to resolve during
    # flush. Referential integrity is enforced at the database level by the
    # Alembic migration's raw ForeignKeyConstraint instead.
    complaint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        unique=True,
    )

    # NLP Outputs
    # index=True omitted: each label column leads a composite index below,
    # making a standalone index on that column redundant for PostgreSQL.
    sentiment_label: Mapped[Optional[SentimentLabel]] = mapped_column(Enum(SentimentLabel))
    urgency_label: Mapped[Optional[UrgencyLabel]] = mapped_column(Enum(UrgencyLabel))
    detected_issue_category: Mapped[Optional[IssueCategory]] = mapped_column(Enum(IssueCategory))
    extracted_keywords: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String(255)))
    complaint_summary: Mapped[Optional[str]] = mapped_column(Text)

    # Model Metadata
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    # server_default keeps this consistent with TimestampMixin and avoids the
    # deprecated datetime.utcnow (removed in Python 3.12) producing naive datetimes.
    enrichment_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    explainability_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Operational Metadata
    processing_latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    enrichment_source: Mapped[str] = mapped_column(String(255), nullable=False)

    # Composite indexes for analytics workloads.
    # Leading columns (sentiment_label, urgency_label, detected_issue_category) do not
    # carry standalone indexes because PostgreSQL can satisfy single-column predicates
    # using a composite index when the column is leftmost.
    __table_args__ = (
        Index("ix_enrichments_sentiment_time", "sentiment_label", "enrichment_timestamp"),
        Index("ix_enrichments_urgency_time", "urgency_label", "enrichment_timestamp"),
        Index("ix_enrichments_issue_time", "detected_issue_category", "enrichment_timestamp"),
    )
