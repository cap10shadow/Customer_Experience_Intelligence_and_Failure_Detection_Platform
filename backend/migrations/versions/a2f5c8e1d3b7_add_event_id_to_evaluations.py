"""add_event_id_to_evaluations

Revision ID: a2f5c8e1d3b7
Revises: 1185033beadf
Create Date: 2026-07-28 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2f5c8e1d3b7"
down_revision: Union[str, Sequence[str], None] = "1185033beadf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add event_id to evaluations for Phase 8 Step 3 (execution lifecycle)."""
    op.add_column("evaluations", sa.Column("event_id", sa.UUID(), nullable=True))
    # UNIQUE, not a composite/partial index: PostgreSQL does not enforce
    # uniqueness across NULLs, so pre-Step-3 rows (event_id IS NULL) and any
    # Evaluation persisted outside the event-driven lifecycle are unaffected.
    # This constraint is the database-backed correctness guarantee behind
    # EvaluationLifecycleService's application-level idempotency check --
    # it is what actually prevents two concurrent deliveries of the same
    # inbound event from ever producing two Evaluations.
    op.create_unique_constraint(op.f("uq_evaluations_event_id"), "evaluations", ["event_id"])


def downgrade() -> None:
    """Drop event_id from evaluations."""
    op.drop_constraint(op.f("uq_evaluations_event_id"), "evaluations", type_="unique")
    op.drop_column("evaluations", "event_id")
