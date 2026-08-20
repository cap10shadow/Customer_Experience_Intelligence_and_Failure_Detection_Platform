"""add_dataset_id_to_business_impact_assessments

Revision ID: d3f6a8b2c537
Revises: c2e5f7a1b426
Create Date: 2026-08-17 00:15:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.shared.constants.seed_ids import LEGACY_DATASET_ID

# revision identifiers, used by Alembic.
revision: str = "d3f6a8b2c537"
down_revision: Union[str, Sequence[str], None] = "c2e5f7a1b426"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Dataset scoping for `business_impact_assessments` (docs/DECISIONS.md
    AD-12) -- gains `dataset_id`, NOT NULL from the start, backfilled to
    the same fixed Legacy/Demo dataset every pre-existing complaint was
    backfilled into (migration `a1c3d5e7f902`), never left null/orphaned.
    """
    op.add_column("business_impact_assessments", sa.Column("dataset_id", sa.UUID(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE business_impact_assessments SET dataset_id = :dataset_id WHERE dataset_id IS NULL"
        ).bindparams(dataset_id=LEGACY_DATASET_ID)
    )
    op.alter_column("business_impact_assessments", "dataset_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_business_impact_assessments_dataset_id_datasets"),
        "business_impact_assessments",
        "datasets",
        ["dataset_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_business_impact_assessments_dataset_id"), "business_impact_assessments", ["dataset_id"], unique=False
    )


def downgrade() -> None:
    """Reverts business_impact_assessments to its pre-dataset-scoping shape."""
    op.drop_index(op.f("ix_business_impact_assessments_dataset_id"), table_name="business_impact_assessments")
    op.drop_constraint(
        op.f("fk_business_impact_assessments_dataset_id_datasets"), "business_impact_assessments", type_="foreignkey"
    )
    op.drop_column("business_impact_assessments", "dataset_id")
