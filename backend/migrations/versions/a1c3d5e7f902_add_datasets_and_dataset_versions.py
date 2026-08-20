"""add_datasets_and_dataset_versions

Revision ID: a1c3d5e7f902
Revises: e35a123597e1
Create Date: 2026-08-17 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.shared.constants.seed_ids import LEGACY_DATASET_ID, LEGACY_DATASET_VERSION_ID

# revision identifiers, used by Alembic.
revision: str = "a1c3d5e7f902"
# Rebased onto the actual pre-existing head (e35a123597e1, the gateway
# identity/Copilot-ownership chain) -- this migration was originally
# authored against a stale down_revision (f05ea2afc3ee), which had
# already grown a sibling chain (b3c8e5a1f204 onward) by the time this
# revision was created. Left as-is, `alembic upgrade head` would fail
# with two divergent heads; see docs/DECISIONS.md AD-12.
down_revision: Union[str, Sequence[str], None] = "e35a123597e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DATASETS_TABLE = sa.table(
    "datasets",
    sa.column("id", sa.UUID()),
    sa.column("name", sa.String()),
    sa.column("description", sa.Text()),
    sa.column("created_by", sa.UUID()),
    sa.column("is_deleted", sa.Boolean()),
    sa.column("inserted_at", sa.DateTime(timezone=True)),
)

_DATASET_VERSIONS_TABLE = sa.table(
    "dataset_versions",
    sa.column("id", sa.UUID()),
    sa.column("dataset_id", sa.UUID()),
    sa.column("version_number", sa.Integer()),
    # Must match the real column's native Postgres enum type -- a plain
    # `sa.String()` here binds the backfill value as VARCHAR, which
    # Postgres refuses to insert into a `datasetversionstatus` column
    # without an explicit cast.
    sa.column(
        "status",
        sa.Enum(
            "DRAFT", "INGESTING", "PROCESSING", "ANALYZING", "READY", "FAILED", "PARTIALLY_COMPLETED",
            name="datasetversionstatus",
        ),
    ),
    sa.column("cumulative_record_count", sa.Integer()),
    sa.column("new_record_count", sa.Integer()),
    sa.column("analysis_completed_at", sa.DateTime(timezone=True)),
    sa.column("inserted_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    """
    Introduces the Dataset/DatasetVersion domain model (docs/DECISIONS.md
    AD-12): the platform's first genuine notion of "which analytical
    workspace does this data belong to." Every pre-existing complaint is
    real data (seed/demo rows loaded via backend/tooling/seed_data, or
    anything ingested before this migration ran) -- backfilled into one
    fixed "Legacy / Demo Data" dataset + version 1 rather than left with
    a null/orphaned reference, so `complaints.dataset_id` can be a real
    NOT NULL foreign key from the moment this migration completes, not an
    opt-in filter a query can forget to apply.
    """
    op.create_table(
        "datasets",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inserted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_datasets")),
    )
    op.create_index(op.f("ix_datasets_is_deleted"), "datasets", ["is_deleted"], unique=False)

    op.create_table(
        "dataset_versions",
        sa.Column("dataset_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT", "INGESTING", "PROCESSING", "ANALYZING", "READY", "FAILED", "PARTIALLY_COMPLETED",
                name="datasetversionstatus",
            ),
            nullable=False,
        ),
        sa.Column("cumulative_record_count", sa.Integer(), nullable=False),
        sa.Column("new_record_count", sa.Integer(), nullable=False),
        sa.Column("analysis_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("analysis_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inserted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"], ["datasets.id"], name=op.f("fk_dataset_versions_dataset_id_datasets"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dataset_versions")),
        sa.UniqueConstraint(
            "dataset_id", "version_number", name="uq_dataset_versions_dataset_id_version_number"
        ),
    )
    op.create_index(op.f("ix_dataset_versions_dataset_id"), "dataset_versions", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_dataset_versions_status"), "dataset_versions", ["status"], unique=False)

    # --- Backfill: one fixed Legacy/Demo dataset + version 1 -------------
    op.bulk_insert(
        _DATASETS_TABLE,
        [
            {
                "id": LEGACY_DATASET_ID,
                "name": "Legacy / Demo Data",
                "description": (
                    "Complaints ingested before dataset tracking existed -- operator-run seed data and any "
                    "records created via the single-record ingestion API prior to this migration. Assigned "
                    "here automatically so no existing record is left without a real dataset."
                ),
                "created_by": None,
                "is_deleted": False,
                # `inserted_at` deliberately omitted -- the column's own
                # `server_default=sa.text("now()")` fills it in. Passing
                # `sa.func.now()` here would bind it as a literal asyncpg
                # query parameter (an unevaluated SQL-expression object,
                # not a real timestamp), which asyncpg rejects outright.
            }
        ],
    )
    complaint_count = op.get_bind().execute(sa.text("SELECT COUNT(*) FROM complaints")).scalar_one()
    op.bulk_insert(
        _DATASET_VERSIONS_TABLE,
        [
            {
                "id": LEGACY_DATASET_VERSION_ID,
                "dataset_id": LEGACY_DATASET_ID,
                "version_number": 1,
                "status": "READY",
                "cumulative_record_count": complaint_count,
                "new_record_count": complaint_count,
                "analysis_completed_at": None,
            }
        ],
    )

    # --- complaints.dataset_id / dataset_version_id: add nullable, backfill, then lock down --
    op.add_column("complaints", sa.Column("dataset_id", sa.UUID(), nullable=True))
    op.add_column("complaints", sa.Column("dataset_version_id", sa.UUID(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE complaints SET dataset_id = :dataset_id, dataset_version_id = :version_id "
            "WHERE dataset_id IS NULL"
        ).bindparams(dataset_id=LEGACY_DATASET_ID, version_id=LEGACY_DATASET_VERSION_ID)
    )
    op.alter_column("complaints", "dataset_id", nullable=False)
    op.alter_column("complaints", "dataset_version_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_complaints_dataset_id_datasets"), "complaints", "datasets", ["dataset_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_foreign_key(
        op.f("fk_complaints_dataset_version_id_dataset_versions"),
        "complaints",
        "dataset_versions",
        ["dataset_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_complaints_dataset_id"), "complaints", ["dataset_id"], unique=False)
    op.create_index(
        op.f("ix_complaints_dataset_version_id"), "complaints", ["dataset_version_id"], unique=False
    )
    op.create_index(
        "ix_complaints_dataset_id_occurred_at", "complaints", ["dataset_id", "event_occurred_at"], unique=False
    )


def downgrade() -> None:
    """Drops dataset_id from complaints, then dataset_versions/datasets and the DatasetVersionStatus enum."""
    op.drop_index("ix_complaints_dataset_id_occurred_at", table_name="complaints")
    op.drop_index(op.f("ix_complaints_dataset_version_id"), table_name="complaints")
    op.drop_index(op.f("ix_complaints_dataset_id"), table_name="complaints")
    op.drop_constraint(op.f("fk_complaints_dataset_version_id_dataset_versions"), "complaints", type_="foreignkey")
    op.drop_constraint(op.f("fk_complaints_dataset_id_datasets"), "complaints", type_="foreignkey")
    op.drop_column("complaints", "dataset_version_id")
    op.drop_column("complaints", "dataset_id")

    op.drop_index(op.f("ix_dataset_versions_status"), table_name="dataset_versions")
    op.drop_index(op.f("ix_dataset_versions_dataset_id"), table_name="dataset_versions")
    op.drop_table("dataset_versions")
    op.execute(sa.text("DROP TYPE IF EXISTS datasetversionstatus"))

    op.drop_index(op.f("ix_datasets_is_deleted"), table_name="datasets")
    op.drop_table("datasets")
