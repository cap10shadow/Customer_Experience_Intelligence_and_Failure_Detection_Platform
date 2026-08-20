"""add_dataset_id_to_recommendations

Revision ID: e4a7b9c3d648
Revises: d3f6a8b2c537
Create Date: 2026-08-17 00:20:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.shared.constants.seed_ids import LEGACY_DATASET_ID

# revision identifiers, used by Alembic.
revision: str = "e4a7b9c3d648"
down_revision: Union[str, Sequence[str], None] = "d3f6a8b2c537"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Dataset scoping for `recommendations` and `recommendation_generations`
    (docs/DECISIONS.md AD-12) -- both gain `dataset_id`, NOT NULL from the
    start, backfilled to the same fixed Legacy/Demo dataset every
    pre-existing complaint was backfilled into (migration
    `a1c3d5e7f902`), never left null/orphaned.
    """
    # --- recommendation_generations -----------------------------------
    op.add_column("recommendation_generations", sa.Column("dataset_id", sa.UUID(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE recommendation_generations SET dataset_id = :dataset_id WHERE dataset_id IS NULL"
        ).bindparams(dataset_id=LEGACY_DATASET_ID)
    )
    op.alter_column("recommendation_generations", "dataset_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_recommendation_generations_dataset_id_datasets"),
        "recommendation_generations",
        "datasets",
        ["dataset_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_recommendation_generations_dataset_id"), "recommendation_generations", ["dataset_id"], unique=False
    )

    # --- recommendations -------------------------------------------------
    op.add_column("recommendations", sa.Column("dataset_id", sa.UUID(), nullable=True))
    op.execute(
        sa.text("UPDATE recommendations SET dataset_id = :dataset_id WHERE dataset_id IS NULL").bindparams(
            dataset_id=LEGACY_DATASET_ID
        )
    )
    op.alter_column("recommendations", "dataset_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_recommendations_dataset_id_datasets"),
        "recommendations",
        "datasets",
        ["dataset_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_recommendations_dataset_id"), "recommendations", ["dataset_id"], unique=False)


def downgrade() -> None:
    """Reverts recommendations and recommendation_generations to their pre-dataset-scoping shape."""
    op.drop_index(op.f("ix_recommendations_dataset_id"), table_name="recommendations")
    op.drop_constraint(op.f("fk_recommendations_dataset_id_datasets"), "recommendations", type_="foreignkey")
    op.drop_column("recommendations", "dataset_id")

    op.drop_index(op.f("ix_recommendation_generations_dataset_id"), table_name="recommendation_generations")
    op.drop_constraint(
        op.f("fk_recommendation_generations_dataset_id_datasets"), "recommendation_generations", type_="foreignkey"
    )
    op.drop_column("recommendation_generations", "dataset_id")
