"""add_business_impact_assessments_table

Revision ID: 73006d54dc8f
Revises: 9d2a7c4e1f6b
Create Date: 2026-07-23 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "73006d54dc8f"
down_revision: Union[str, Sequence[str], None] = "9d2a7c4e1f6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create business_impact_assessments table for Phase 7 Step 2."""
    op.create_table(
        "business_impact_assessments",
        sa.Column("incident_id", sa.UUID(), nullable=False),
        sa.Column("root_cause_id", sa.UUID(), nullable=False),
        sa.Column(
            "financial",
            sa.Enum("NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL", name="impactlevel"),
            nullable=False,
        ),
        sa.Column(
            "customer",
            sa.Enum("NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL", name="impactlevel"),
            nullable=False,
        ),
        sa.Column(
            "operational",
            sa.Enum("NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL", name="impactlevel"),
            nullable=False,
        ),
        sa.Column(
            "sla",
            sa.Enum("NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL", name="impactlevel"),
            nullable=False,
        ),
        sa.Column(
            "reputation",
            sa.Enum("NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL", name="impactlevel"),
            nullable=False,
        ),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column(
            "overall_severity",
            sa.Enum("NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL", name="impactlevel"),
            nullable=False,
        ),
        sa.Column(
            "business_priority",
            sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="businesspriority"),
            nullable=False,
        ),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("estimated_affected_customers", sa.Integer(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", name="businessimpactassessmentstatus"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("assessment_id", sa.UUID(), nullable=False),
        # Referential integrity to `incidents.id` (owned by the Anomaly
        # Service) and `root_causes.id` (owned by the Root Cause Service) is
        # enforced here, at the database level, via raw ForeignKeyConstraints
        # -- not ORM ForeignKeys (see DATA-001 / DATA-002). The Business
        # Impact Service never registers either table in its own SQLAlchemy
        # metadata.
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name=op.f("fk_business_impact_assessments_incident_id_incidents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["root_cause_id"],
            ["root_causes.id"],
            name=op.f("fk_business_impact_assessments_root_cause_id_root_causes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("assessment_id", name=op.f("pk_business_impact_assessments")),
        # Deliberately no UniqueConstraint on incident_id: unlike RootCause
        # (exactly one per Incident), an Incident may accumulate multiple
        # immutable BusinessImpactAssessment snapshots over time as trend/
        # anomaly data evolves.
    )
    op.create_index(
        op.f("ix_business_impact_assessments_incident_id"),
        "business_impact_assessments",
        ["incident_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_business_impact_assessments_root_cause_id"),
        "business_impact_assessments",
        ["root_cause_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_business_impact_assessments_overall_severity"),
        "business_impact_assessments",
        ["overall_severity"],
        unique=False,
    )
    op.create_index(
        op.f("ix_business_impact_assessments_business_priority"),
        "business_impact_assessments",
        ["business_priority"],
        unique=False,
    )
    op.create_index(
        op.f("ix_business_impact_assessments_status"),
        "business_impact_assessments",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Drop business_impact_assessments table and its enum types."""
    op.drop_index(op.f("ix_business_impact_assessments_status"), table_name="business_impact_assessments")
    op.drop_index(
        op.f("ix_business_impact_assessments_business_priority"), table_name="business_impact_assessments"
    )
    op.drop_index(
        op.f("ix_business_impact_assessments_overall_severity"), table_name="business_impact_assessments"
    )
    op.drop_index(op.f("ix_business_impact_assessments_root_cause_id"), table_name="business_impact_assessments")
    op.drop_index(op.f("ix_business_impact_assessments_incident_id"), table_name="business_impact_assessments")
    op.drop_table("business_impact_assessments")

    op.execute(sa.text("DROP TYPE IF EXISTS businessimpactassessmentstatus"))
    op.execute(sa.text("DROP TYPE IF EXISTS businesspriority"))
    op.execute(sa.text("DROP TYPE IF EXISTS impactlevel"))
