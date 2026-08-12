"""add_decision_to_recommendations

Revision ID: f05ea2afc3ee
Revises: d4b6e2f8a1c3
Create Date: 2026-08-12 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f05ea2afc3ee"
down_revision: Union[str, Sequence[str], None] = "d4b6e2f8a1c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Adds minimal decision persistence to `recommendations` (Step 7.X
    G-01) -- three nullable columns, additive only. Every pre-existing
    row gets NULL for all three, correctly representing "no decision was
    ever recorded for this Recommendation" rather than a fabricated
    historical decision. No decision-owner/actor column is added -- see
    RecommendationDecision's own docstring for why.
    """
    op.add_column(
        "recommendations",
        sa.Column(
            "decision",
            sa.Enum("PENDING", "APPROVED", "REJECTED", "DEFERRED", name="recommendationdecision"),
            nullable=True,
        ),
    )
    op.add_column("recommendations", sa.Column("decision_note", sa.Text(), nullable=True))
    op.add_column("recommendations", sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Drops the three decision columns and the RecommendationDecision enum type."""
    op.drop_column("recommendations", "decided_at")
    op.drop_column("recommendations", "decision_note")
    op.drop_column("recommendations", "decision")
    op.execute("DROP TYPE IF EXISTS recommendationdecision")
