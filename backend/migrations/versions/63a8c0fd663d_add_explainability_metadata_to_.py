"""add_explainability_metadata_to_complaint_enrichment

Revision ID: 63a8c0fd663d
Revises: 3a1f2b8c5e09
Create Date: 2026-06-12 18:13:29.248197

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '63a8c0fd663d'
down_revision: Union[str, Sequence[str], None] = '3a1f2b8c5e09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('complaint_enrichments', sa.Column('explainability_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('complaint_enrichments', 'explainability_metadata')
