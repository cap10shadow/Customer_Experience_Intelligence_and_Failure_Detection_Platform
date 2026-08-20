"""add_dataset_id_to_root_causes

Revision ID: c2e5f7a1b426
Revises: b8d4e6f0a315
Create Date: 2026-08-17 00:10:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.shared.constants.seed_ids import LEGACY_DATASET_ID

# revision identifiers, used by Alembic.
revision: str = "c2e5f7a1b426"
down_revision: Union[str, Sequence[str], None] = "b8d4e6f0a315"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Dataset scoping for `root_causes` (docs/DECISIONS.md AD-12) -- gains
    `dataset_id`, NOT NULL from the start, backfilled to the same fixed
    Legacy/Demo dataset every pre-existing complaint was backfilled into
    (migration `a1c3d5e7f902`), never left null/orphaned.
    """
    op.add_column("root_causes", sa.Column("dataset_id", sa.UUID(), nullable=True))
    op.execute(
        sa.text("UPDATE root_causes SET dataset_id = :dataset_id WHERE dataset_id IS NULL").bindparams(
            dataset_id=LEGACY_DATASET_ID
        )
    )
    op.alter_column("root_causes", "dataset_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_root_causes_dataset_id_datasets"),
        "root_causes",
        "datasets",
        ["dataset_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_root_causes_dataset_id"), "root_causes", ["dataset_id"], unique=False)


def downgrade() -> None:
    """Reverts root_causes to its pre-dataset-scoping shape."""
    op.drop_index(op.f("ix_root_causes_dataset_id"), table_name="root_causes")
    op.drop_constraint(op.f("fk_root_causes_dataset_id_datasets"), "root_causes", type_="foreignkey")
    op.drop_column("root_causes", "dataset_id")
