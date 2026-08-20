"""Add unique constraint on complaint source_record_hash

Revision ID: d8e2f4a6b719
Revises: c9d1a4e7b520
Create Date: 2026-08-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd8e2f4a6b719'
down_revision: Union[str, Sequence[str], None] = 'c9d1a4e7b520'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Closes a TOCTOU duplicate-detection race (WP-E stabilization pass):
    dedup was previously check-then-insert against a plain, non-unique
    index on source_record_hash -- two concurrent/retried requests for
    the same record could both pass the `exists`/`bulk_exists` check
    before either commits, producing two Complaint rows with the same
    hash. NULLs (rows ingested before this hash existed, if any) remain
    unconstrained -- Postgres never treats two NULLs as equal, so this
    only enforces uniqueness among rows that actually have a hash.
    """
    op.drop_index(op.f('ix_complaints_source_record_hash'), table_name='complaints')
    op.create_unique_constraint(op.f('uq_complaints_source_record_hash'), 'complaints', ['source_record_hash'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f('uq_complaints_source_record_hash'), 'complaints', type_='unique')
    op.create_index(op.f('ix_complaints_source_record_hash'), 'complaints', ['source_record_hash'], unique=False)
