import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.database.base import Base, PrimaryKeyMixin

"""
Gateway-owned identity persistence (Phase 13 Batch 1, AD-1 --
docs/architecture/phase-13/PHASE_13_ARCHITECTURE.md §7/§8;
docs/DECISIONS.md AD-1). `gateway_service` is the exclusive owner of
these three tables in the platform's existing shared PostgreSQL
instance (ARCH-002); no other service reads or writes them directly
(DATA-002). This is Gateway's first persistence responsibility -- it
previously owned no database tables of its own.

Batch 1 scope only: these are the identity/domain models and the
database migration. Public authentication routes, JWT issuance, RBAC
enforcement, and any Gateway middleware that consumes these models are
explicitly out of scope here and belong to later Phase 13 batches
(§32 of the frozen architecture).
"""


class User(Base, PrimaryKeyMixin):
    """
    A project-owned platform identity. `password_hash` is never
    plaintext (bcrypt, see app/core/security.py) and is never included
    in any API response DTO -- no DTO exists yet in this batch, but the
    column itself carries no serialization concerns since the ORM model
    is never returned directly by a route.

    `is_active` is a soft-deactivation flag, matching this platform's
    existing convention of state flags over destructive deletes
    (ANOMALY-001's active/resolved lifecycle is the same pattern).
    `last_login_at` is nullable and is only ever set by the future
    login flow (Batch 3) -- Batch 1 never sets it.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Deliberately no `onupdate=func.now()`: SQLAlchemy's async ORM marks
    # an onupdate-computed column "expired" after every UPDATE rather
    # than eagerly refreshing it within the awaited flush, and a later
    # synchronous attribute read crashes with MissingGreenlet outside an
    # async context. Every other mutable timestamp in this codebase
    # (root_causes.updated_at, ActiveAnomaly.last_seen_at) is instead set
    # explicitly in application code -- whichever future batch mutates a
    # User row (e.g. deactivation) must follow that same, already-proven
    # pattern rather than relying on `onupdate`.
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None)


class Role(Base, PrimaryKeyMixin):
    """
    A named platform role (`viewer` / `operator` / `admin` per §11 of
    the frozen architecture). Batch 1 defines the table only -- it does
    not seed these three rows and does not enforce any RBAC permission;
    both are explicitly later-batch scope (§32, Batch 4). `name` is
    unique so a role can be looked up deterministically by name once a
    later batch needs to.
    """

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)


class UserRole(Base):
    """
    The `users` <-> `roles` join table. Composite primary key (no
    surrogate id), matching the frozen architecture's exact schema
    (§8). Both foreign keys are real ORM/DB constraints -- unlike a
    cross-service reference, `users`/`roles`/`user_roles` are all owned
    by `gateway_service`, so this follows the same same-service FK
    precedent already established by `copilot_messages` ->
    `copilot_conversations` (DATA-001/DATA-002 only restrict
    *cross-service* ORM coupling, not FKs within one service's own
    tables). `ondelete="CASCADE"` keeps `user_roles` consistent if a
    user or role row is ever removed -- no delete flow exists yet in
    this batch.
    """

    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
