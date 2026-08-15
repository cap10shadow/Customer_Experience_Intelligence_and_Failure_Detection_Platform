"""seed_gateway_roles

Revision ID: 12fef1ff2286
Revises: 7cc83da82812
Create Date: 2026-08-15 11:49:15.073857

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "12fef1ff2286"
down_revision: Union[str, Sequence[str], None] = "7cc83da82812"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ROLES_TABLE = sa.table(
    "roles",
    sa.column("id", sa.UUID()),
    sa.column("name", sa.String()),
    sa.column("description", sa.Text()),
)

_ROLE_NAMES = ("viewer", "operator", "admin")
_ROLE_DESCRIPTIONS = {
    "viewer": "Read-only access to every GET route (§11/§12, docs/architecture/phase-13/PHASE_13_ARCHITECTURE.md).",
    "operator": "viewer + the recommendation-decision PATCH route and Copilot.",
    "admin": "operator + reserved for future administrative mutation capability -- no exclusive capability exists yet (documented honestly in §11, not fabricated scope).",
}


def upgrade() -> None:
    """
    Phase 13 Batch 3 (RBAC, frozen architecture §11/§12): seeds the
    three canonical role rows the permission matrix names. Data-only,
    additive -- no schema change, no user account, no password, no
    role assignment (`user_roles` stays empty; assigning a role to a
    specific user remains an explicit, separate, out-of-migration
    action). Looked up by `name` everywhere in application code, so the
    UUIDs generated here are never hardcoded elsewhere.
    """
    op.bulk_insert(
        _ROLES_TABLE,
        [{"id": uuid.uuid4(), "name": name, "description": _ROLE_DESCRIPTIONS[name]} for name in _ROLE_NAMES],
    )


def downgrade() -> None:
    op.execute(_ROLES_TABLE.delete().where(_ROLES_TABLE.c.name.in_(_ROLE_NAMES)))
