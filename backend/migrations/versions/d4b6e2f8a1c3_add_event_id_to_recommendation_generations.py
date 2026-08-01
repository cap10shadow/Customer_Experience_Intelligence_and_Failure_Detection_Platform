"""add_event_id_to_recommendation_generations

Revision ID: d4b6e2f8a1c3
Revises: c7a1f9d4b2e6
Create Date: 2026-08-02 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4b6e2f8a1c3"
down_revision: Union[str, Sequence[str], None] = "c7a1f9d4b2e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add event_id to recommendation_generations for Phase 9 Step 3 (execution lifecycle)."""
    op.add_column("recommendation_generations", sa.Column("event_id", sa.UUID(), nullable=True))
    # UNIQUE, not a composite/partial index: PostgreSQL does not enforce
    # uniqueness across NULLs, so pre-Step-3 rows (event_id IS NULL) and any
    # RecommendationGeneration persisted outside the event-driven lifecycle
    # are unaffected. This constraint is the database-backed correctness
    # guarantee behind RecommendationLifecycleService's application-level
    # idempotency check -- it is what actually prevents two concurrent
    # deliveries of the same inbound event from ever producing two
    # RecommendationGenerations.
    op.create_unique_constraint(
        op.f("uq_recommendation_generations_event_id"), "recommendation_generations", ["event_id"]
    )


def downgrade() -> None:
    """Drop event_id from recommendation_generations."""
    op.drop_constraint(
        op.f("uq_recommendation_generations_event_id"), "recommendation_generations", type_="unique"
    )
    op.drop_column("recommendation_generations", "event_id")
