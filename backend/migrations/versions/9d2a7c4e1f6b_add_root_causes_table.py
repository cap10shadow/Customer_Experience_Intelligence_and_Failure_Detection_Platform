"""add_root_causes_table

Revision ID: 9d2a7c4e1f6b
Revises: 4b8e1d6a9c2f
Create Date: 2026-07-21 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9d2a7c4e1f6b"
down_revision: Union[str, Sequence[str], None] = "4b8e1d6a9c2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create root_causes table for Phase 6 Step 2."""
    op.create_table(
        "root_causes",
        sa.Column("incident_id", sa.UUID(), nullable=False),
        sa.Column(
            "cause",
            sa.Enum(
                "PAYMENT_GATEWAY_FAILURE", "LOGISTICS_DELAY", "SERVICE_OUTAGE", "AUTHENTICATION_FAILURE",
                "INVENTORY_SHORTAGE", "CUSTOMER_SUPPORT_DELAY", "UNKNOWN",
                name="rootcause",
            ),
            nullable=False,
        ),
        sa.Column("confidence_score", sa.Integer(), nullable=False),
        sa.Column("confidence_level", sa.String(length=20), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("rule_version", sa.String(length=20), nullable=False),
        sa.Column(
            "status",
            sa.Enum("IDENTIFIED", "CONFIRMED", "REJECTED", name="rootcausestatus"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        # Referential integrity to `incidents.id` (owned by the Anomaly
        # Service) is enforced here, at the database level, via a raw
        # ForeignKeyConstraint — not an ORM ForeignKey (see DATA-001 /
        # DATA-002). The Root Cause Service never registers the `incidents`
        # table in its own SQLAlchemy metadata.
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name=op.f("fk_root_causes_incident_id_incidents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_root_causes")),
        sa.UniqueConstraint("incident_id", name=op.f("uq_root_causes_incident_id")),
    )
    op.create_index(op.f("ix_root_causes_cause"), "root_causes", ["cause"], unique=False)
    op.create_index(op.f("ix_root_causes_status"), "root_causes", ["status"], unique=False)
    op.create_index(op.f("ix_root_causes_incident_id"), "root_causes", ["incident_id"], unique=False)


def downgrade() -> None:
    """Drop root_causes table and its enum types."""
    op.drop_index(op.f("ix_root_causes_incident_id"), table_name="root_causes")
    op.drop_index(op.f("ix_root_causes_status"), table_name="root_causes")
    op.drop_index(op.f("ix_root_causes_cause"), table_name="root_causes")
    op.drop_table("root_causes")

    op.execute(sa.text("DROP TYPE IF EXISTS rootcausestatus"))
    op.execute(sa.text("DROP TYPE IF EXISTS rootcause"))
