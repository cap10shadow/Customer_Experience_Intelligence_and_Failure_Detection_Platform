"""add_dataset_version_id_provenance

Revision ID: f7b1c4d8e953
Revises: e4a7b9c3d648
Create Date: 2026-08-17 02:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.shared.constants.seed_ids import LEGACY_DATASET_VERSION_ID

# revision identifiers, used by Alembic.
revision: str = "f7b1c4d8e953"
down_revision: Union[str, Sequence[str], None] = "e4a7b9c3d648"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    True version-addressable intelligence (AD-12 follow-up): `dataset_id`
    alone cannot distinguish which DatasetVersion's analysis run produced
    a given RootCause/BusinessImpactAssessment/Recommendation -- extending
    a dataset to Version 2 and re-running analysis had no way to keep
    Version 1's already-produced intelligence independently addressable
    from Version 2's. `dataset_version_id` here is a real FK into
    `dataset_versions`, set exactly once at row creation (never mutated
    afterward, unlike `active_anomalies`/`incidents`' own mutable
    `last_analysis_version_id`, which is a "last touched by" pointer on a
    continuously-reconciled row, not a creation-time fact). Since
    RootCause is a create-once-per-incident singleton and
    BusinessImpactAssessment/Recommendation already accumulate a new row
    per analysis run (never overwritten), this column alone is enough to
    query "the assessment/recommendation(s) produced for Version N"
    independently of whatever Version is current now.

    Backfilled to `LEGACY_DATASET_VERSION_ID`, the fixed Version 1 every
    pre-existing row was implicitly produced under before this column
    existed (same rationale as `LEGACY_DATASET_ID`'s own backfill in
    `a1c3d5e7f902`).
    """
    # --- root_causes -------------------------------------------------------
    op.add_column("root_causes", sa.Column("dataset_version_id", sa.UUID(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE root_causes SET dataset_version_id = :version_id WHERE dataset_version_id IS NULL"
        ).bindparams(version_id=LEGACY_DATASET_VERSION_ID)
    )
    op.alter_column("root_causes", "dataset_version_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_root_causes_dataset_version_id_dataset_versions"),
        "root_causes",
        "dataset_versions",
        ["dataset_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_root_causes_dataset_version_id"), "root_causes", ["dataset_version_id"], unique=False
    )

    # --- business_impact_assessments ---------------------------------------
    op.add_column("business_impact_assessments", sa.Column("dataset_version_id", sa.UUID(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE business_impact_assessments SET dataset_version_id = :version_id "
            "WHERE dataset_version_id IS NULL"
        ).bindparams(version_id=LEGACY_DATASET_VERSION_ID)
    )
    op.alter_column("business_impact_assessments", "dataset_version_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_business_impact_assessments_dataset_version_id_dataset_versions"),
        "business_impact_assessments",
        "dataset_versions",
        ["dataset_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_business_impact_assessments_dataset_version_id"),
        "business_impact_assessments",
        ["dataset_version_id"],
        unique=False,
    )

    # --- recommendation_generations -----------------------------------------
    op.add_column("recommendation_generations", sa.Column("dataset_version_id", sa.UUID(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE recommendation_generations SET dataset_version_id = :version_id "
            "WHERE dataset_version_id IS NULL"
        ).bindparams(version_id=LEGACY_DATASET_VERSION_ID)
    )
    op.alter_column("recommendation_generations", "dataset_version_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_recommendation_generations_dataset_version_id_dataset_versions"),
        "recommendation_generations",
        "dataset_versions",
        ["dataset_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_recommendation_generations_dataset_version_id"),
        "recommendation_generations",
        ["dataset_version_id"],
        unique=False,
    )

    # --- recommendations -----------------------------------------------------
    op.add_column("recommendations", sa.Column("dataset_version_id", sa.UUID(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE recommendations SET dataset_version_id = :version_id WHERE dataset_version_id IS NULL"
        ).bindparams(version_id=LEGACY_DATASET_VERSION_ID)
    )
    op.alter_column("recommendations", "dataset_version_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_recommendations_dataset_version_id_dataset_versions"),
        "recommendations",
        "dataset_versions",
        ["dataset_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_recommendations_dataset_version_id"), "recommendations", ["dataset_version_id"], unique=False
    )

    # --- anomaly_history -------------------------------------------------------
    # Same rationale, applied to the one domain that already has genuine
    # append-only point-in-time snapshots (`metrics_snapshot` JSONB) --
    # tagging each history event with the version whose analysis run wrote
    # it makes "what did this anomaly look like as of Version N" a real,
    # queryable fact instead of only inferable from a timestamp.
    op.add_column("anomaly_history", sa.Column("dataset_version_id", sa.UUID(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE anomaly_history SET dataset_version_id = :version_id WHERE dataset_version_id IS NULL"
        ).bindparams(version_id=LEGACY_DATASET_VERSION_ID)
    )
    op.alter_column("anomaly_history", "dataset_version_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_anomaly_history_dataset_version_id_dataset_versions"),
        "anomaly_history",
        "dataset_versions",
        ["dataset_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_anomaly_history_dataset_version_id"), "anomaly_history", ["dataset_version_id"], unique=False
    )


def downgrade() -> None:
    """Reverts every table above to its pre-version-provenance shape."""
    op.drop_index(op.f("ix_anomaly_history_dataset_version_id"), table_name="anomaly_history")
    op.drop_constraint(
        op.f("fk_anomaly_history_dataset_version_id_dataset_versions"), "anomaly_history", type_="foreignkey"
    )
    op.drop_column("anomaly_history", "dataset_version_id")

    op.drop_index(op.f("ix_recommendations_dataset_version_id"), table_name="recommendations")
    op.drop_constraint(
        op.f("fk_recommendations_dataset_version_id_dataset_versions"), "recommendations", type_="foreignkey"
    )
    op.drop_column("recommendations", "dataset_version_id")

    op.drop_index(op.f("ix_recommendation_generations_dataset_version_id"), table_name="recommendation_generations")
    op.drop_constraint(
        op.f("fk_recommendation_generations_dataset_version_id_dataset_versions"),
        "recommendation_generations",
        type_="foreignkey",
    )
    op.drop_column("recommendation_generations", "dataset_version_id")

    op.drop_index(op.f("ix_business_impact_assessments_dataset_version_id"), table_name="business_impact_assessments")
    op.drop_constraint(
        op.f("fk_business_impact_assessments_dataset_version_id_dataset_versions"),
        "business_impact_assessments",
        type_="foreignkey",
    )
    op.drop_column("business_impact_assessments", "dataset_version_id")

    op.drop_index(op.f("ix_root_causes_dataset_version_id"), table_name="root_causes")
    op.drop_constraint(
        op.f("fk_root_causes_dataset_version_id_dataset_versions"), "root_causes", type_="foreignkey"
    )
    op.drop_column("root_causes", "dataset_version_id")
