"""extend_operational_area_taxonomy

Revision ID: a4c9e1f7d382
Revises: f7b1c4d8e953
Create Date: 2026-08-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4c9e1f7d382"
down_revision: Union[str, Sequence[str], None] = "f7b1c4d8e953"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_VALUES = ["PACKAGING", "REFUNDS", "ORDER_MANAGEMENT", "FULFILLMENT"]


def upgrade() -> None:
    """
    Ingestion was rejecting legitimate complaint rows whose
    `operational_area` was "Packaging", "Refunds", or "Order Management" --
    the `OperationalArea` taxonomy simply never covered those business
    concepts (backend/shared/constants/enums/business_impact.py). This adds
    the missing values to the Postgres `operationalarea` enum type so the
    schema matches the widened Python enum. `ALTER TYPE ... ADD VALUE`
    cannot run inside a transaction block, hence `AUTOCOMMIT`.
    """
    with op.get_context().autocommit_block():
        for value in NEW_VALUES:
            op.execute(f"ALTER TYPE operationalarea ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    """
    Postgres cannot drop individual enum values in place; rebuilding the
    type would require rewriting the `complaints.operational_area` column,
    which is out of scope for reverting this additive change. Downgrade is
    intentionally a no-op.
    """
    pass
