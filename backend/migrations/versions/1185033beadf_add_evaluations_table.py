"""add_evaluations_table

Revision ID: 1185033beadf
Revises: 73006d54dc8f
Create Date: 2026-07-25 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "1185033beadf"
down_revision: Union[str, Sequence[str], None] = "73006d54dc8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create evaluations table for Phase 8 Step 2."""
    op.create_table(
        "evaluations",
        sa.Column("incident_id", sa.String(length=64), nullable=False),
        sa.Column("root_cause_id", sa.UUID(), nullable=True),
        sa.Column("business_impact_id", sa.UUID(), nullable=True),
        sa.Column("evaluation_version", sa.String(length=20), nullable=False),
        sa.Column("previous_evaluation_id", sa.UUID(), nullable=True),
        sa.Column("validation_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quality_assessment", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("explainability_assessment", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        # clock_timestamp(), not now(): now() is transaction-scoped and
        # would return an identical value for every row inserted within the
        # same transaction, making ORDER BY created_at DESC (get_latest,
        # list_by_incident) non-deterministic for ties. clock_timestamp()
        # is evaluated per-statement.
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.Column("evaluation_id", sa.UUID(), nullable=False),
        # No ForeignKeyConstraint to incidents.id, root_causes.id, or
        # business_impact_assessments.assessment_id: the Evaluation Service
        # never registers those services' tables in its own metadata and
        # must remain independently deployable (DATA-002). Referential
        # integrity for incident_id is intentionally not enforced at the
        # database level either, since this table's rows are an
        # out-of-band, append-only audit trail that must never be blocked
        # or cascaded by upstream deletes.
        sa.PrimaryKeyConstraint("evaluation_id", name=op.f("pk_evaluations")),
    )
    op.create_index(op.f("ix_evaluations_incident_id"), "evaluations", ["incident_id"], unique=False)
    op.create_index(
        "ix_evaluations_incident_id_evaluation_version",
        "evaluations",
        ["incident_id", sa.text("evaluation_version DESC")],
        unique=False,
    )


def downgrade() -> None:
    """Drop evaluations table."""
    op.drop_index("ix_evaluations_incident_id_evaluation_version", table_name="evaluations")
    op.drop_index(op.f("ix_evaluations_incident_id"), table_name="evaluations")
    op.drop_table("evaluations")
