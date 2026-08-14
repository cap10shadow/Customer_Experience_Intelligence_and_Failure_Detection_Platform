"""add_copilot_conversations_and_messages

Revision ID: b3c8e5a1f204
Revises: f05ea2afc3ee
Create Date: 2026-08-13 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b3c8e5a1f204"
down_revision: Union[str, Sequence[str], None] = "f05ea2afc3ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create copilot_conversations and copilot_messages tables for Phase 12
    Batch 4 (conversation persistence, architecture §17 / COPILOT-002).
    Additive only -- no existing table is touched.
    """
    op.create_table(
        "copilot_conversations",
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("workspace", sa.String(length=50), nullable=True),
        sa.Column("incident_id", sa.String(length=64), nullable=True),
        sa.Column("recommendation_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("conversation_id", name=op.f("pk_copilot_conversations")),
    )

    op.create_table(
        "copilot_messages",
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("sequence", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("USER", "ASSISTANT", name="copilotmessagerole"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("evidence_references", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # Real ORM/DB ForeignKey: both tables are owned by copilot_service
        # (see CopilotMessage's own docstring for why this differs from
        # the raw ForeignKeyConstraint-without-ORM-relationship pattern
        # used for cross-service references elsewhere in this platform).
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["copilot_conversations.conversation_id"],
            name=op.f("fk_copilot_messages_conversation_id_copilot_conversations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("message_id", name=op.f("pk_copilot_messages")),
        sa.UniqueConstraint("sequence", name=op.f("uq_copilot_messages_sequence")),
    )
    op.create_index(
        "ix_copilot_messages_conversation_id_sequence",
        "copilot_messages",
        ["conversation_id", "sequence"],
        unique=False,
    )


def downgrade() -> None:
    """Drop copilot_messages and copilot_conversations tables and the role enum type."""
    op.drop_index("ix_copilot_messages_conversation_id_sequence", table_name="copilot_messages")
    op.drop_table("copilot_messages")
    op.execute(sa.text("DROP TYPE IF EXISTS copilotmessagerole"))

    op.drop_table("copilot_conversations")
