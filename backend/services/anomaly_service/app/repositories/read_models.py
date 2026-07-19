from sqlalchemy import Boolean, Column, DateTime, Enum, MetaData, String, Table
from sqlalchemy.dialects.postgresql import UUID

from backend.shared.constants.enums.complaint import IssueCategory, SentimentLabel, UrgencyLabel

# Dedicated MetaData instance, intentionally separate from the shared
# declarative `Base` used by other services. The Trend Engine only ever
# reads from `complaints` and `complaint_enrichments` — tables owned by the
# ingestion and NLP services respectively — and must never import those
# services' ORM model classes to stay independently deployable. These Table
# objects are unmapped (no ORM entities, no relationships) and declare only
# the columns trend analytics actually reads.
read_models_metadata = MetaData()

complaints_table = Table(
    "complaints",
    read_models_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("customer_region", String(100)),
    Column("event_occurred_at", DateTime(timezone=True)),
    Column("is_deleted", Boolean, nullable=False),
)

complaint_enrichments_table = Table(
    "complaint_enrichments",
    read_models_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("complaint_id", UUID(as_uuid=True)),
    Column("sentiment_label", Enum(SentimentLabel)),
    Column("urgency_label", Enum(UrgencyLabel)),
    Column("detected_issue_category", Enum(IssueCategory)),
    Column("enrichment_timestamp", DateTime(timezone=True)),
)
