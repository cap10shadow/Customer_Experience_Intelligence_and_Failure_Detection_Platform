"""add_dataset_scoping_to_anomalies_and_incidents

Revision ID: b8d4e6f0a315
Revises: a1c3d5e7f902
Create Date: 2026-08-17 00:05:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.shared.constants.seed_ids import LEGACY_DATASET_ID, LEGACY_DATASET_VERSION_ID

# revision identifiers, used by Alembic.
revision: str = "b8d4e6f0a315"
down_revision: Union[str, Sequence[str], None] = "a1c3d5e7f902"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Dataset scoping for `active_anomalies` and `incidents`
    (docs/DECISIONS.md AD-12) -- both gain `dataset_id` (isolation: every
    list/reconcile query filters by it) and `last_analysis_version_id`
    (provenance: which analysis run last touched this row), both NOT NULL
    from the start, backfilled to the same fixed Legacy/Demo dataset every
    pre-existing complaint was backfilled into (migration
    `a1c3d5e7f902`), never left null/orphaned.

    `active_anomalies.fingerprint` was globally UNIQUE; two different
    datasets can legitimately produce the identical fingerprint (e.g.
    "complaint_spike:global:ALL") without colliding, so the constraint is
    replaced with a composite UNIQUE(fingerprint, dataset_id).
    """
    # --- active_anomalies -------------------------------------------------
    op.add_column("active_anomalies", sa.Column("dataset_id", sa.UUID(), nullable=True))
    op.add_column("active_anomalies", sa.Column("last_analysis_version_id", sa.UUID(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE active_anomalies SET dataset_id = :dataset_id, last_analysis_version_id = :version_id "
            "WHERE dataset_id IS NULL"
        ).bindparams(dataset_id=LEGACY_DATASET_ID, version_id=LEGACY_DATASET_VERSION_ID)
    )
    op.alter_column("active_anomalies", "dataset_id", nullable=False)
    op.alter_column("active_anomalies", "last_analysis_version_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_active_anomalies_dataset_id_datasets"),
        "active_anomalies",
        "datasets",
        ["dataset_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_active_anomalies_last_analysis_version_id_dataset_versions"),
        "active_anomalies",
        "dataset_versions",
        ["last_analysis_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_active_anomalies_dataset_id"), "active_anomalies", ["dataset_id"], unique=False)
    op.create_index(
        op.f("ix_active_anomalies_last_analysis_version_id"),
        "active_anomalies",
        ["last_analysis_version_id"],
        unique=False,
    )

    op.drop_constraint(op.f("uq_active_anomalies_fingerprint"), "active_anomalies", type_="unique")
    op.create_unique_constraint(
        "uq_active_anomalies_fingerprint_dataset_id", "active_anomalies", ["fingerprint", "dataset_id"]
    )

    # --- incidents ----------------------------------------------------------
    op.add_column("incidents", sa.Column("dataset_id", sa.UUID(), nullable=True))
    op.add_column("incidents", sa.Column("last_analysis_version_id", sa.UUID(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE incidents SET dataset_id = :dataset_id, last_analysis_version_id = :version_id "
            "WHERE dataset_id IS NULL"
        ).bindparams(dataset_id=LEGACY_DATASET_ID, version_id=LEGACY_DATASET_VERSION_ID)
    )
    op.alter_column("incidents", "dataset_id", nullable=False)
    op.alter_column("incidents", "last_analysis_version_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_incidents_dataset_id_datasets"), "incidents", "datasets", ["dataset_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_foreign_key(
        op.f("fk_incidents_last_analysis_version_id_dataset_versions"),
        "incidents",
        "dataset_versions",
        ["last_analysis_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_incidents_dataset_id"), "incidents", ["dataset_id"], unique=False)
    op.create_index(
        op.f("ix_incidents_last_analysis_version_id"), "incidents", ["last_analysis_version_id"], unique=False
    )


def downgrade() -> None:
    """Reverts incidents and active_anomalies to their pre-dataset-scoping shape."""
    op.drop_index(op.f("ix_incidents_last_analysis_version_id"), table_name="incidents")
    op.drop_index(op.f("ix_incidents_dataset_id"), table_name="incidents")
    op.drop_constraint(op.f("fk_incidents_last_analysis_version_id_dataset_versions"), "incidents", type_="foreignkey")
    op.drop_constraint(op.f("fk_incidents_dataset_id_datasets"), "incidents", type_="foreignkey")
    op.drop_column("incidents", "last_analysis_version_id")
    op.drop_column("incidents", "dataset_id")

    op.drop_constraint("uq_active_anomalies_fingerprint_dataset_id", "active_anomalies", type_="unique")
    op.create_unique_constraint(op.f("uq_active_anomalies_fingerprint"), "active_anomalies", ["fingerprint"])

    op.drop_index(op.f("ix_active_anomalies_last_analysis_version_id"), table_name="active_anomalies")
    op.drop_index(op.f("ix_active_anomalies_dataset_id"), table_name="active_anomalies")
    op.drop_constraint(
        op.f("fk_active_anomalies_last_analysis_version_id_dataset_versions"), "active_anomalies", type_="foreignkey"
    )
    op.drop_constraint(op.f("fk_active_anomalies_dataset_id_datasets"), "active_anomalies", type_="foreignkey")
    op.drop_column("active_anomalies", "last_analysis_version_id")
    op.drop_column("active_anomalies", "dataset_id")
