"""add_active_anomalies_and_anomaly_history_tables

Revision ID: 7f3c9d2a1b4e
Revises: 63a8c0fd663d
Create Date: 2026-07-19 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7f3c9d2a1b4e"
down_revision: Union[str, Sequence[str], None] = "63a8c0fd663d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create active_anomalies and anomaly_history tables for Phase 5 Step 2."""
    op.create_table(
        "active_anomalies",
        sa.Column("fingerprint", sa.String(length=255), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "COMPLAINT_SPIKE", "REGIONAL_SPIKE", "CATEGORY_SPIKE", "URGENCY_SPIKE",
                "SENTIMENT_SHIFT", "ESCALATION_SURGE", "OPERATIONAL_DEGRADATION",
                "CHURN_RISK_SURGE", "ABNORMAL_PATTERN",
                name="anomalytype",
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum("NORMAL", "LOW", "MEDIUM", "HIGH", "CRITICAL", name="anomalyseverity"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_value", sa.String(length=255), nullable=True),
        sa.Column("baseline_value", sa.Float(), nullable=False),
        sa.Column("current_value", sa.Float(), nullable=False),
        sa.Column("percentage_change", sa.Float(), nullable=True),
        sa.Column("triggered_rule", sa.String(length=255), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "RESOLVED", name="anomalystatus"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "inserted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_active_anomalies")),
        sa.UniqueConstraint("fingerprint", name=op.f("uq_active_anomalies_fingerprint")),
    )
    op.create_index(
        op.f("ix_active_anomalies_entity_type"), "active_anomalies", ["entity_type"], unique=False
    )
    op.create_index(
        op.f("ix_active_anomalies_last_seen_at"), "active_anomalies", ["last_seen_at"], unique=False
    )
    op.create_index(op.f("ix_active_anomalies_status"), "active_anomalies", ["status"], unique=False)
    op.create_index(op.f("ix_active_anomalies_severity"), "active_anomalies", ["severity"], unique=False)
    op.create_index(op.f("ix_active_anomalies_type"), "active_anomalies", ["type"], unique=False)

    op.create_table(
        "anomaly_history",
        sa.Column("active_anomaly_id", sa.UUID(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum("DETECTED", "UPDATED", "RESOLVED", name="anomalyeventtype"),
            nullable=False,
        ),
        sa.Column(
            "old_severity",
            sa.Enum("NORMAL", "LOW", "MEDIUM", "HIGH", "CRITICAL", name="anomalyseverity"),
            nullable=True,
        ),
        sa.Column(
            "new_severity",
            sa.Enum("NORMAL", "LOW", "MEDIUM", "HIGH", "CRITICAL", name="anomalyseverity"),
            nullable=True,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("metrics_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "inserted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["active_anomaly_id"],
            ["active_anomalies.id"],
            name=op.f("fk_anomaly_history_active_anomaly_id_active_anomalies"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_anomaly_history")),
    )
    op.create_index(
        op.f("ix_anomaly_history_active_anomaly_id"), "anomaly_history", ["active_anomaly_id"], unique=False
    )
    op.create_index(
        op.f("ix_anomaly_history_event_timestamp"), "anomaly_history", ["event_timestamp"], unique=False
    )
    op.create_index(op.f("ix_anomaly_history_event_type"), "anomaly_history", ["event_type"], unique=False)


def downgrade() -> None:
    """Drop anomaly_history and active_anomalies tables and their enum types."""
    op.drop_index(op.f("ix_anomaly_history_event_type"), table_name="anomaly_history")
    op.drop_index(op.f("ix_anomaly_history_event_timestamp"), table_name="anomaly_history")
    op.drop_index(op.f("ix_anomaly_history_active_anomaly_id"), table_name="anomaly_history")
    op.drop_table("anomaly_history")

    op.drop_index(op.f("ix_active_anomalies_type"), table_name="active_anomalies")
    op.drop_index(op.f("ix_active_anomalies_severity"), table_name="active_anomalies")
    op.drop_index(op.f("ix_active_anomalies_status"), table_name="active_anomalies")
    op.drop_index(op.f("ix_active_anomalies_last_seen_at"), table_name="active_anomalies")
    op.drop_index(op.f("ix_active_anomalies_entity_type"), table_name="active_anomalies")
    op.drop_table("active_anomalies")

    op.execute(sa.text("DROP TYPE IF EXISTS anomalyeventtype"))
    op.execute(sa.text("DROP TYPE IF EXISTS anomalystatus"))
    op.execute(sa.text("DROP TYPE IF EXISTS anomalyseverity"))
    op.execute(sa.text("DROP TYPE IF EXISTS anomalytype"))
