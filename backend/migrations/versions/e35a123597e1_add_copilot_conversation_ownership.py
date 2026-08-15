"""add_copilot_conversation_ownership

Revision ID: e35a123597e1
Revises: b097f212d868
Create Date: 2026-08-15 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e35a123597e1"
down_revision: Union[str, Sequence[str], None] = "b097f212d868"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Phase 13 Batch 6 (AD-4, docs/architecture/phase-13/PHASE_13_ARCHITECTURE.md
    §16/§17, docs/DECISIONS.md AD-4): Copilot conversation ownership.

    `copilot_conversations.owner_id` -- one new nullable column,
    additive only. Nullable to preserve every pre-Phase-13 conversation
    row (they remain permanently orphaned/inaccessible per AD-4's own
    documented consequence -- no retroactive ownership assignment);
    every conversation created from this point forward is required, at
    the application layer (`copilot_service`), to carry a real owner --
    the database itself stays permissive so old rows are never touched
    by this migration. Referential integrity to `gateway_service`'s
    `users.id` (both in the one shared PostgreSQL instance) is enforced
    here via a raw `ForeignKeyConstraint` -- not an ORM `ForeignKey` --
    per the DATA-001/DATA-002 cross-service precedent already
    established by `recommendations.decided_by` -> `users.id`
    (b097f212d868, Phase 13 Batch 5). `ondelete="SET NULL"`: `users` are
    soft-deactivated (`is_active`), never hard-deleted in the platform's
    own normal operation, but if a `users` row is ever actually removed,
    the conversation must survive with its ownership honestly cleared
    (becoming orphaned/inaccessible, the same as a pre-Phase-13 row),
    not be cascade-deleted itself.

    No index is added on `owner_id`: no "list my conversations" query
    exists anywhere in this batch's scope (§17 names no such capability,
    and none is invented here) -- matching this platform's own "add
    indexes only if objectively required" convention (see
    `RecommendationModel`'s docstring for the same principle already
    applied).

    No retention/purge-job migration work is included here: AD-4's
    "technical mechanism" (an optional, disabled-by-default age-based
    purge job and its own `last_message_at` index) is explicitly tied to
    "the same migration as the purge mechanism, not before" -- since no
    purge mechanism is implemented in this batch (not named in the
    frozen architecture's Batch 6-equivalent scope or Definition of
    Done), no such index is added here either. See the Batch 6
    implementation report's carry-forward items.
    """
    op.add_column("copilot_conversations", sa.Column("owner_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_copilot_conversations_owner_id_users"),
        "copilot_conversations",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Drop copilot_conversations.owner_id and its FK constraint."""
    op.drop_constraint(op.f("fk_copilot_conversations_owner_id_users"), "copilot_conversations", type_="foreignkey")
    op.drop_column("copilot_conversations", "owner_id")
