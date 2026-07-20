"""add_incidents_and_incident_anomalies_tables

Revision ID: 4b8e1d6a9c2f
Revises: 7f3c9d2a1b4e
Create Date: 2026-07-20 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4b8e1d6a9c2f"
down_revision: Union[str, Sequence[str], None] = "7f3c9d2a1b4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create incidents and incident_anomalies tables for Phase 5 Step 3."""
    op.create_table(
        "incidents",
        sa.Column("incident_key", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "severity",
            # Reuses the "anomalyseverity" type created by 7f3c9d2a1b4e.
            # create_type=False: this type already exists, so it must not
            # be re-issued as CREATE TYPE (checkfirst does not carry over
            # across separate Alembic migration runs).
            postgresql.ENUM(
                "NORMAL", "LOW", "MEDIUM", "HIGH", "CRITICAL", name="anomalyseverity", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("OPEN", "INVESTIGATING", "MITIGATED", "RESOLVED", name="incidentstatus"),
            nullable=False,
        ),
        sa.Column("confidence_score", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "inserted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incidents")),
        sa.UniqueConstraint("incident_key", name=op.f("uq_incidents_incident_key")),
    )
    op.create_index(op.f("ix_incidents_severity"), "incidents", ["severity"], unique=False)
    op.create_index(op.f("ix_incidents_status"), "incidents", ["status"], unique=False)
    op.create_index(op.f("ix_incidents_last_updated_at"), "incidents", ["last_updated_at"], unique=False)

    op.create_table(
        "incident_anomalies",
        sa.Column("incident_id", sa.UUID(), nullable=False),
        sa.Column("active_anomaly_id", sa.UUID(), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "inserted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name=op.f("fk_incident_anomalies_incident_id_incidents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["active_anomaly_id"],
            ["active_anomalies.id"],
            name=op.f("fk_incident_anomalies_active_anomaly_id_active_anomalies"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incident_anomalies")),
        sa.UniqueConstraint(
            "incident_id", "active_anomaly_id", name="uq_incident_anomalies_incident_active_anomaly"
        ),
    )
    op.create_index(
        op.f("ix_incident_anomalies_incident_id"), "incident_anomalies", ["incident_id"], unique=False
    )
    op.create_index(
        op.f("ix_incident_anomalies_active_anomaly_id"), "incident_anomalies", ["active_anomaly_id"], unique=False
    )


def downgrade() -> None:
    """Drop incident_anomalies and incidents tables and the incidentstatus enum type."""
    op.drop_index(op.f("ix_incident_anomalies_active_anomaly_id"), table_name="incident_anomalies")
    op.drop_index(op.f("ix_incident_anomalies_incident_id"), table_name="incident_anomalies")
    op.drop_table("incident_anomalies")

    op.drop_index(op.f("ix_incidents_last_updated_at"), table_name="incidents")
    op.drop_index(op.f("ix_incidents_status"), table_name="incidents")
    op.drop_index(op.f("ix_incidents_severity"), table_name="incidents")
    op.drop_table("incidents")

    op.execute(sa.text("DROP TYPE IF EXISTS incidentstatus"))
