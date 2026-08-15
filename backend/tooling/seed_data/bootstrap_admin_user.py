"""
Controlled first-user bootstrap (AD-8, docs/DECISIONS.md;
docs/architecture/phase-13/PHASE_13_ARCHITECTURE.md §34).

Not a public endpoint -- there is no `/auth/register` route anywhere in
this platform (see `gateway_service/app/api/auth.py`'s own docstring) and
this script does not add one. This module is run manually by an
operator/developer, after `alembic upgrade head` has already seeded the
`viewer`/`operator`/`admin` roles (`12fef1ff2286_seed_gateway_roles.py`),
to create the platform's first usable login. It is never imported or
invoked by `gateway_service/app/main.py`, any FastAPI startup/lifespan
hook, or any other application entry point -- ordinary application
startup never creates a user.

Configuration comes from two environment variables, `BOOTSTRAP_ADMIN_EMAIL`
and `BOOTSTRAP_ADMIN_PASSWORD`, following this repository's existing
`env_file`-injected convention (matching `INTERNAL_SERVICE_SECRET`, etc.).
Neither has a default value: AD-8 requires bootstrap credentials to be
explicitly supplied in every environment, dev included, so a missing
value fails clearly rather than silently falling back to a guessable
default (unlike `POSTGRES_PASSWORD`-style secrets, this is a real,
single, operator-invoked login credential, not infrastructure glue that
every container needs merely to start).

Reuses `gateway_service`'s own `hash_password` primitive verbatim -- no
second hashing implementation, no second credential format. Email is
compared exactly as supplied, with no normalization, matching
`auth_service.authenticate()`'s own case-sensitive-as-stored behavior
(`UserRepository.get_by_email` does a plain equality lookup; the
platform introduces no lowercasing convention anywhere).

Idempotent: if a user with the configured email already exists, this
script leaves that user's password and role assignment completely
untouched and exits cleanly -- it never resets credentials on a re-run,
and (per AD-8's literal "leaves it untouched" contract) it does not
attempt to repair a missing role on an existing user either. User
creation and role assignment happen in the same database session,
committed together -- if role assignment fails, the user row is rolled
back with it (SQLAlchemy's async session context manager rolls back on
any exception before an explicit `commit()`).

No password policy is enforced beyond "non-empty": no such policy exists
anywhere else in this codebase (no `/auth/register` route to have ever
defined one), and AD-8 does not introduce one -- inventing a length/
complexity policy here would be new, undocumented scope.

Usage:

    python -m backend.tooling.seed_data.bootstrap_admin_user
"""
from __future__ import annotations

import asyncio
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.services.gateway_service.app.core.security import hash_password
from backend.services.gateway_service.app.repositories.identity_repository import RoleRepository, UserRepository
from backend.shared.database.database import async_session_maker

# Matches ROLE_HIERARCHY's exact spelling (gateway_service/app/core/roles.py)
# -- never invented, always the project's real, existing role name.
_BOOTSTRAP_ROLE_NAME = "admin"


class BootstrapSettings(BaseSettings):
    """
    Bootstrap-only configuration. Deliberately separate from
    `GatewaySettings` (gateway_service/app/core/config.py): these
    credentials are needed only by this one-off, operator-invoked
    script, never by the running Gateway application itself, so they
    have no reason to live in the FastAPI app's own settings object.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    BOOTSTRAP_ADMIN_EMAIL: str = ""
    BOOTSTRAP_ADMIN_PASSWORD: str = ""


class BootstrapConfigurationError(Exception):
    """Raised when required bootstrap configuration is missing."""


class BootstrapRoleMissingError(Exception):
    """Raised when the `admin` role has not been seeded yet (migrations haven't run)."""


async def bootstrap_admin_user(*, email: str, password: str) -> str:
    """
    Creates the first administrator user if one doesn't already exist.

    Returns a short, human-readable, secret-free status message. Never
    logs, prints, or returns the plaintext password, the resulting hash,
    or any other secret -- callers must not do so either.
    """
    if not email:
        raise BootstrapConfigurationError("BOOTSTRAP_ADMIN_EMAIL is not configured.")
    if not password:
        raise BootstrapConfigurationError("BOOTSTRAP_ADMIN_PASSWORD is not configured.")

    async with async_session_maker() as session:
        user_repository = UserRepository(session)
        role_repository = RoleRepository(session)

        role = await role_repository.get_by_name(_BOOTSTRAP_ROLE_NAME)
        if role is None:
            raise BootstrapRoleMissingError(
                f"Role '{_BOOTSTRAP_ROLE_NAME}' does not exist yet -- run `alembic upgrade head` first."
            )

        existing_user = await user_repository.get_by_email(email)
        if existing_user is not None:
            return "Bootstrap admin already exists; no password change performed."

        user = await user_repository.create(email=email, password_hash=hash_password(password))
        await role_repository.assign_to_user(user_id=user.id, role_id=role.id)
        await session.commit()
        return "Bootstrap admin created successfully."


async def _main() -> int:
    settings = BootstrapSettings()
    try:
        message = await bootstrap_admin_user(
            email=settings.BOOTSTRAP_ADMIN_EMAIL, password=settings.BOOTSTRAP_ADMIN_PASSWORD
        )
    except (BootstrapConfigurationError, BootstrapRoleMissingError) as exc:
        print(f"Bootstrap failed: {exc}", file=sys.stderr)
        return 1
    print(message)
    return 0


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    sys.exit(asyncio.run(_main()))
