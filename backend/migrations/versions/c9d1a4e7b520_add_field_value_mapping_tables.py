"""add_field_value_mapping_tables

Revision ID: c9d1a4e7b520
Revises: a4c9e1f7d382
Create Date: 2026-08-19 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d1a4e7b520"
down_revision: Union[str, Sequence[str], None] = "a4c9e1f7d382"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CONFIDENCE_ENUM = sa.Enum("HIGH", "MEDIUM", "LOW", name="fieldvaluemappingconfidence")
_STATUS_ENUM = sa.Enum("PENDING", "APPROVED", "REJECTED", name="fieldvaluemappingstatus")
_TYPE_ENUM = sa.Enum("ALIAS", "CANONICAL_SELF", name="fieldvaluemappingtype")


def upgrade() -> None:
    """
    Introduces the ingestion normalization/mapping layer (Ingestion
    Normalization & Mapping Layer plan): a field-scoped, globally-reusable
    record of how raw vocabulary values (customer_region, operational_area)
    resolve to canonical values, a curated alias-suggestion registry that
    powers MEDIUM-confidence suggestions, and a session-based occurrence
    ledger so re-analyzing the same upload never double-counts. This is
    purely additive -- it does NOT touch the `operationalarea` enum type at
    all; enum-constrained targets are validated in the service layer
    against the existing Python enum, never auto-extended here.
    """
    # Enum types are created implicitly by op.create_table() below (each
    # sa.Enum column auto-emits CREATE TYPE the first time it's used) --
    # matching this repo's existing convention (see
    # a1c3d5e7f902_add_datasets_and_dataset_versions.py). No separate
    # explicit .create() call here.
    op.create_table(
        "field_value_mappings",
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("raw_value_normalized", sa.String(length=255), nullable=False),
        sa.Column("raw_value_original_example", sa.String(length=255), nullable=False),
        sa.Column("target_value", sa.String(length=255), nullable=True),
        sa.Column("suggested_target_value", sa.String(length=255), nullable=True),
        sa.Column("confidence", _CONFIDENCE_ENUM, nullable=False),
        sa.Column("mapping_type", _TYPE_ENUM, nullable=True),
        sa.Column("status", _STATUS_ENUM, nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("first_seen_dataset_id", sa.UUID(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inserted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["first_seen_dataset_id"],
            ["datasets.id"],
            name=op.f("fk_field_value_mappings_first_seen_dataset_id_datasets"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_field_value_mappings")),
        sa.UniqueConstraint(
            "field_name", "raw_value_normalized", name="uq_field_value_mappings_field_raw"
        ),
    )
    op.create_index(
        op.f("ix_field_value_mappings_field_name"), "field_value_mappings", ["field_name"], unique=False
    )
    op.create_index(
        "ix_field_value_mappings_field_status", "field_value_mappings", ["field_name", "status"], unique=False
    )
    op.create_index(
        "ix_field_value_mappings_field_confidence_status",
        "field_value_mappings",
        ["field_name", "confidence", "status"],
        unique=False,
    )

    op.create_table(
        "field_alias_suggestions",
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("source_value_normalized", sa.String(length=255), nullable=False),
        sa.Column("suggested_target_value", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inserted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_field_alias_suggestions")),
        sa.UniqueConstraint(
            "field_name", "source_value_normalized", name="uq_field_alias_suggestions_field_source"
        ),
    )
    op.create_index(
        op.f("ix_field_alias_suggestions_field_name"), "field_alias_suggestions", ["field_name"], unique=False
    )

    op.create_table(
        "field_value_mapping_occurrence_sessions",
        sa.Column("mapping_id", sa.UUID(), nullable=False),
        sa.Column("analysis_session_id", sa.UUID(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inserted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["mapping_id"],
            ["field_value_mappings.id"],
            name=op.f("fk_field_value_mapping_occurrence_sessions_mapping_id_field_value_mappings"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_field_value_mapping_occurrence_sessions")),
        sa.UniqueConstraint(
            "mapping_id",
            "analysis_session_id",
            name="uq_field_value_mapping_occurrence_sessions_mapping_session",
        ),
    )
    op.create_index(
        op.f("ix_field_value_mapping_occurrence_sessions_mapping_id"),
        "field_value_mapping_occurrence_sessions",
        ["mapping_id"],
        unique=False,
    )

    op.add_column("complaints", sa.Column("raw_customer_region", sa.String(length=100), nullable=True))
    op.add_column("complaints", sa.Column("raw_operational_area", sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Drops the two new complaints columns, all three new tables, and their new enum types (none pre-existing, so a clean drop carries no data-loss asymmetry)."""
    op.drop_column("complaints", "raw_operational_area")
    op.drop_column("complaints", "raw_customer_region")

    op.drop_index(
        op.f("ix_field_value_mapping_occurrence_sessions_mapping_id"),
        table_name="field_value_mapping_occurrence_sessions",
    )
    op.drop_table("field_value_mapping_occurrence_sessions")

    op.drop_index(op.f("ix_field_alias_suggestions_field_name"), table_name="field_alias_suggestions")
    op.drop_table("field_alias_suggestions")

    op.drop_index("ix_field_value_mappings_field_confidence_status", table_name="field_value_mappings")
    op.drop_index("ix_field_value_mappings_field_status", table_name="field_value_mappings")
    op.drop_index(op.f("ix_field_value_mappings_field_name"), table_name="field_value_mappings")
    op.drop_table("field_value_mappings")

    op.execute(sa.text("DROP TYPE IF EXISTS fieldvaluemappingtype"))
    op.execute(sa.text("DROP TYPE IF EXISTS fieldvaluemappingstatus"))
    op.execute(sa.text("DROP TYPE IF EXISTS fieldvaluemappingconfidence"))
