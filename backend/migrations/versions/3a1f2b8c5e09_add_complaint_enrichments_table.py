"""Add complaint_enrichments table

Revision ID: 3a1f2b8c5e09
Revises: 66239761b187
Create Date: 2026-05-31 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3a1f2b8c5e09"
down_revision: Union[str, Sequence[str], None] = "66239761b187"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create complaint_enrichments table with FK, unique constraint, and analytics indexes."""
    op.create_table(
        "complaint_enrichments",
        # --- Identity & Linkage ---
        sa.Column("complaint_id", sa.UUID(), nullable=False),
        # --- NLP Classification Outputs ---
        sa.Column(
            "sentiment_label",
            sa.Enum(
                "POSITIVE", "NEUTRAL", "NEGATIVE", "HIGHLY_NEGATIVE",
                name="sentimentlabel",
            ),
            nullable=True,
        ),
        sa.Column(
            "urgency_label",
            sa.Enum(
                "LOW", "MEDIUM", "HIGH", "CRITICAL",
                name="urgencylabel",
            ),
            nullable=True,
        ),
        sa.Column(
            "detected_issue_category",
            sa.Enum(
                "DELIVERY_ISSUE", "PAYMENT_ISSUE", "PRODUCT_ISSUE", "SUPPORT_ISSUE",
                "TECHNICAL_ISSUE", "ACCOUNT_ISSUE", "REFUND_ISSUE", "SUBSCRIPTION_ISSUE",
                "SERVICE_DELAY", "OPERATIONAL_FAILURE",
                name="issuecategory",
            ),
            nullable=True,
        ),
        sa.Column("extracted_keywords", sa.ARRAY(sa.String(length=255)), nullable=True),
        sa.Column("complaint_summary", sa.Text(), nullable=True),
        # --- Model Traceability ---
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column(
            "enrichment_timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # --- Operational Metadata ---
        sa.Column("processing_latency_ms", sa.Integer(), nullable=True),
        sa.Column("enrichment_source", sa.String(length=255), nullable=False),
        # --- Mixin Columns (PrimaryKeyMixin, TimestampMixin) ---
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "inserted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # --- Constraints ---
        sa.ForeignKeyConstraint(
            ["complaint_id"],
            ["complaints.id"],
            name=op.f("fk_complaint_enrichments_complaint_id_complaints"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_complaint_enrichments")),
        # Enforces 1:1 linkage at the database level; PostgreSQL creates an
        # implicit unique index for this constraint — no separate index needed.
        sa.UniqueConstraint(
            "complaint_id",
            name=op.f("uq_complaint_enrichments_complaint_id"),
        ),
    )

    # Composite analytics indexes.
    # sentiment_label, urgency_label, and detected_issue_category do NOT receive
    # standalone indexes: each is the leading column of its composite index, so
    # PostgreSQL can satisfy single-column predicates via those composites.
    op.create_index(
        "ix_enrichments_sentiment_time",
        "complaint_enrichments",
        ["sentiment_label", "enrichment_timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_enrichments_urgency_time",
        "complaint_enrichments",
        ["urgency_label", "enrichment_timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_enrichments_issue_time",
        "complaint_enrichments",
        ["detected_issue_category", "enrichment_timestamp"],
        unique=False,
    )

    # Standalone index on enrichment_timestamp for time-range queries that do not
    # filter by label (e.g. "all enrichments in the last 24 hours").
    op.create_index(
        op.f("ix_complaint_enrichments_enrichment_timestamp"),
        "complaint_enrichments",
        ["enrichment_timestamp"],
        unique=False,
    )


def downgrade() -> None:
    """Drop complaint_enrichments table and the enum types created exclusively for it."""
    op.drop_index(
        op.f("ix_complaint_enrichments_enrichment_timestamp"),
        table_name="complaint_enrichments",
    )
    op.drop_index("ix_enrichments_issue_time", table_name="complaint_enrichments")
    op.drop_index("ix_enrichments_urgency_time", table_name="complaint_enrichments")
    op.drop_index("ix_enrichments_sentiment_time", table_name="complaint_enrichments")
    op.drop_table("complaint_enrichments")

    # Drop PostgreSQL enum types that were created for this table and are not
    # shared with any other table. Order: most-derived first.
    op.execute(sa.text("DROP TYPE IF EXISTS issuecategory"))
    op.execute(sa.text("DROP TYPE IF EXISTS urgencylabel"))
    op.execute(sa.text("DROP TYPE IF EXISTS sentimentlabel"))
