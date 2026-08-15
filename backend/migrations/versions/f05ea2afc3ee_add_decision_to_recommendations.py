"""add_decision_to_recommendations

Revision ID: f05ea2afc3ee
Revises: d4b6e2f8a1c3
Create Date: 2026-08-12 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

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

    AD-7 (revised, docs/DECISIONS.md; docs/architecture/phase-13/
    PHASE_13_ARCHITECTURE.md §34): `op.add_column`, unlike
    `op.create_table`, does not implicitly `CREATE TYPE` a Postgres enum
    before referencing it -- against a genuinely empty database the
    original version of this migration failed here with
    `UndefinedObjectError: type "recommendationdecision" does not exist`.
    The enum type is now explicitly ensured first (`checkfirst=True`, a
    safe no-op if it already exists), then the column is added exactly as
    before. Values/casing are unchanged. A first attempt at this fix used
    a separate migration positioned after the current head, but that
    cannot work: Alembic executes the chain strictly in order and aborts
    the whole run the moment this migration's own `upgrade()` raises, so
    a later migration is never reached on a fresh database. Fixing it
    here, where the defect actually is, is the only mechanism that
    works for a fresh database in a single pass.
    """
    recommendation_decision_enum = postgresql.ENUM(
        "PENDING", "APPROVED", "REJECTED", "DEFERRED", name="recommendationdecision"
    )
    recommendation_decision_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "recommendations",
        sa.Column(
            "decision",
            postgresql.ENUM(
                "PENDING", "APPROVED", "REJECTED", "DEFERRED", name="recommendationdecision", create_type=False
            ),
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
