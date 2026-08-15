"""add_recommendation_decision_attribution

Revision ID: b097f212d868
Revises: 12fef1ff2286
Create Date: 2026-08-15 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b097f212d868"
down_revision: Union[str, Sequence[str], None] = "12fef1ff2286"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Phase 13 Batch 5 (AD-3, docs/architecture/phase-13/PHASE_13_ARCHITECTURE.md
    §14/§15, docs/DECISIONS.md AD-3): recommendation decision attribution
    and an append-only decision history.

    `recommendations.decided_by` -- one new nullable column, additive
    only, matching the existing `decision`/`decision_note`/`decided_at`
    convention (Step 7.X G-01): every pre-Phase-13 row gets NULL,
    correctly meaning "no known actor" rather than a fabricated one.
    Referential integrity to `gateway_service`'s `users.id` (both in the
    one shared PostgreSQL instance) is enforced here via a raw
    `ForeignKeyConstraint` -- not an ORM `ForeignKey` -- per the
    DATA-001/DATA-002 cross-service precedent already established by
    `root_causes.incident_id` -> `incidents.id`. `ondelete="SET NULL"`:
    `users` are soft-deactivated (`is_active`), never hard-deleted in
    the platform's own normal operation, but if a `users` row is ever
    actually removed, the attributed Recommendation must survive with
    its attribution honestly cleared, not be cascade-deleted itself.

    `recommendation_decision_history` -- new, service-owned, append-only
    table, per AD-3's exact column list: `id`, `recommendation_id`,
    `decision`, `decision_note`, `actor_id`, `created_at`. Reuses the
    existing `recommendationdecision` enum type (already created by
    f05ea2afc3ee) rather than declaring a second one.
    `recommendation_id` -> `recommendations.recommendation_id` is a real
    same-service FK (both tables owned by recommendation_service,
    matching the `copilot_messages` -> `copilot_conversations`
    precedent) -- AD-3 calls this FK "not required... but recommended
    for integrity". `actor_id` -> `users.id` is the same cross-service,
    `ondelete="SET NULL"` pattern as `recommendations.decided_by` above,
    for the identical reason. `created_at` uses `clock_timestamp()`, not
    `now()`, matching `recommendations.created_at`/
    `recommendation_generations.created_at`'s own established rationale
    (deterministic ordering for ties within one transaction).
    """
    op.add_column("recommendations", sa.Column("decided_by", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_recommendations_decided_by_users"),
        "recommendations",
        "users",
        ["decided_by"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "recommendation_decision_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("recommendation_id", sa.UUID(), nullable=False),
        sa.Column(
            "decision",
            postgresql.ENUM("PENDING", "APPROVED", "REJECTED", "DEFERRED", name="recommendationdecision", create_type=False),
            nullable=False,
        ),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_id"],
            ["recommendations.recommendation_id"],
            name=op.f("fk_rec_decision_history_recommendation_id_recommendations"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name=op.f("fk_recommendation_decision_history_actor_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_decision_history")),
    )
    op.create_index(
        "ix_recommendation_decision_history_recommendation_id",
        "recommendation_decision_history",
        ["recommendation_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop recommendation_decision_history and recommendations.decided_by, in FK-safe reverse order."""
    op.drop_index(
        "ix_recommendation_decision_history_recommendation_id", table_name="recommendation_decision_history"
    )
    op.drop_table("recommendation_decision_history")

    op.drop_constraint(op.f("fk_recommendations_decided_by_users"), "recommendations", type_="foreignkey")
    op.drop_column("recommendations", "decided_by")
