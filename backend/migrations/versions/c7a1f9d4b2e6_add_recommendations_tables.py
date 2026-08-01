"""add_recommendations_tables

Revision ID: c7a1f9d4b2e6
Revises: a2f5c8e1d3b7
Create Date: 2026-08-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c7a1f9d4b2e6"
down_revision: Union[str, Sequence[str], None] = "a2f5c8e1d3b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create recommendation_generations and recommendations tables for Phase 9 Step 2."""
    op.create_table(
        "recommendation_generations",
        # generation_id has no server-side default: per the frozen
        # architecture, Generation identifiers are created in Step 3 --
        # Step 2 only ever persists a value supplied by its caller.
        sa.Column("generation_id", sa.UUID(), nullable=False),
        sa.Column("incident_id", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("generation_id", name=op.f("pk_recommendation_generations")),
    )
    op.create_index(
        "ix_recommendation_generations_incident_id_created_at",
        "recommendation_generations",
        ["incident_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "recommendations",
        sa.Column("recommendation_id", sa.UUID(), nullable=False),
        sa.Column("incident_id", sa.String(length=64), nullable=False),
        sa.Column("generation_id", sa.UUID(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "MONITOR",
                "INVESTIGATE",
                "MITIGATE",
                "ESCALATE",
                "CUSTOMER_COMMUNICATION",
                "INFRASTRUCTURE_ACTION",
                "OPERATIONAL_ACTION",
                "SLA_PROTECTION",
                name="recommendationcategory",
            ),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Enum("CRITICAL", "HIGH", "MEDIUM", "LOW", name="recommendationpriority"),
            nullable=False,
        ),
        sa.Column("score", sa.Integer(), nullable=False),
        # Not part of the frozen column list -- required to avoid silently
        # losing Recommendation.action, a required Step 1 domain field with
        # no other column to persist it in. See RecommendationModel's own
        # docstring and the Step 2 implementation report's Deviations
        # section for the full explanation.
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("recommendation_rationale", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("priority_rationale", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("supporting_evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False
        ),
        # No ForeignKeyConstraint to recommendation_generations.generation_id
        # or to incidents.id: consistent with DATA-001/DATA-002 as already
        # applied to every other service's tables in this platform --
        # referential integrity for incident_id is intentionally not
        # enforced at the database level, and the generation_id relationship
        # is a plain identifier column, not a declared ORM relationship().
        sa.PrimaryKeyConstraint("recommendation_id", name=op.f("pk_recommendations")),
    )
    op.create_index(
        "ix_recommendations_incident_id_generation_id",
        "recommendations",
        ["incident_id", "generation_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop recommendations and recommendation_generations tables."""
    op.drop_index("ix_recommendations_incident_id_generation_id", table_name="recommendations")
    op.drop_table("recommendations")
    op.execute("DROP TYPE IF EXISTS recommendationcategory")
    op.execute("DROP TYPE IF EXISTS recommendationpriority")

    op.drop_index("ix_recommendation_generations_incident_id_created_at", table_name="recommendation_generations")
    op.drop_table("recommendation_generations")
