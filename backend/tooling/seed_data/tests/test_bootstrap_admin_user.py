"""
Tests for the controlled first-user bootstrap script (AD-8).

Real-PostgreSQL tests only (no mocking of persistence) -- the only way to
genuinely verify idempotency, role assignment, and that a password is
never persisted in plaintext. Connects to `localhost:5432` (the same
Postgres `docker compose up postgres` exposes) and skips cleanly if not
reachable, matching this repository's own established convention (see
`gateway_service/tests/test_identity_repository.py`). Self-sufficient:
creates the `users`/`roles`/`user_roles` tables and seeds the three
canonical roles itself if they don't already exist, so this suite does
not require a prior `alembic upgrade head` to run.

Every test uses a unique, clearly-marked email under `_TEST_EMAIL_PREFIX`
and cleans up its own rows afterward -- this script commits for real
(that is correct production behavior), so tests cannot rely on an outer
rolled-back transaction the way pure-repository tests do.
"""

import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.services.gateway_service.app.core.security import verify_password
from backend.services.gateway_service.app.main import app as gateway_app
from backend.services.gateway_service.app.models.identity import Role, User, UserRole
from backend.shared.config.settings import Settings
from backend.shared.database.database import engine as _shared_engine
from backend.tooling.seed_data.bootstrap_admin_user import (
    BootstrapConfigurationError,
    BootstrapRoleMissingError,
    bootstrap_admin_user,
)

_TEST_EMAIL_PREFIX = "bootstrap-test-"
_ROLE_NAMES = ("viewer", "operator", "admin")

_test_settings = Settings(POSTGRES_HOST="localhost")
_test_engine = create_async_engine(_test_settings.database_url, poolclass=NullPool)

_database_available: Optional[bool] = None


async def _is_database_available() -> bool:
    global _database_available
    if _database_available is None:
        try:
            async with _test_engine.connect() as probe:
                await probe.execute(text("SELECT 1"))
            _database_available = True
        except Exception:
            _database_available = False
    return _database_available


@asynccontextmanager
async def _prepared_session() -> AsyncIterator[AsyncSession]:
    """
    Ensures the identity tables and the three canonical roles exist
    (checkfirst/idempotent), then yields a plain session for the test to
    use for direct verification queries. Bootstrap itself always opens
    its own session via `async_session_maker()` (the real production
    path), not this one.
    """
    if not await _is_database_available():
        pytest.skip("PostgreSQL is not reachable on localhost:5432 -- run `docker compose up postgres` to enable these tests")

    async with _test_engine.connect() as conn:
        await conn.run_sync(lambda sync_conn: User.__table__.create(sync_conn, checkfirst=True))  # type: ignore[attr-defined]
        await conn.run_sync(lambda sync_conn: Role.__table__.create(sync_conn, checkfirst=True))  # type: ignore[attr-defined]
        await conn.run_sync(lambda sync_conn: UserRole.__table__.create(sync_conn, checkfirst=True))  # type: ignore[attr-defined]
        await conn.commit()

        session = AsyncSession(bind=conn, expire_on_commit=False)
        for name in _ROLE_NAMES:
            existing = await session.execute(text("SELECT id FROM roles WHERE name = :name"), {"name": name})
            if existing.scalar_one_or_none() is None:
                await session.execute(
                    text("INSERT INTO roles (id, name, description) VALUES (:id, :name, :description)"),
                    {"id": str(uuid.uuid4()), "name": name, "description": f"test-seeded {name} role"},
                )
        await session.commit()
        try:
            yield session
        finally:
            await session.close()


async def _cleanup_test_users(session: AsyncSession) -> None:
    """Removes every row this test suite may have created -- never touches a real, non-test user."""
    await session.execute(
        text("DELETE FROM user_roles WHERE user_id IN (SELECT id FROM users WHERE email LIKE :prefix)"),
        {"prefix": f"{_TEST_EMAIL_PREFIX}%"},
    )
    await session.execute(text("DELETE FROM users WHERE email LIKE :prefix"), {"prefix": f"{_TEST_EMAIL_PREFIX}%"})
    await session.commit()


def _unique_test_email() -> str:
    return f"{_TEST_EMAIL_PREFIX}{uuid.uuid4().hex}@example.invalid"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def _dispose_shared_engine_after_each_test():
    """
    `bootstrap_admin_user()` deliberately uses the real, shared,
    production `async_session_maker()` (backend/shared/database/
    database.py) -- not a test-local engine -- since that is the exact
    code path a real operator invocation exercises. That shared engine's
    connection pool is created once at import time; pytest-anyio gives
    each test function its own event loop, and a pooled asyncpg
    connection cannot outlive the event loop it was opened on. Disposing
    the pool after every test (test-level only, no application code
    touched) forces a fresh connection on the next test's loop instead
    of a stale one, which otherwise surfaces as a spurious
    "Event loop is closed" failure unrelated to bootstrap's own logic.
    """
    yield
    await _shared_engine.dispose()


@pytest.mark.anyio
async def test_creates_user_with_hashed_password_and_admin_role(_dispose_shared_engine_after_each_test):
    async with _prepared_session() as session:
        email = _unique_test_email()
        try:
            message = await bootstrap_admin_user(email=email, password="a-real-bootstrap-password")

            assert message == "Bootstrap admin created successfully."

            row = await session.execute(text("SELECT id, password_hash FROM users WHERE email = :email"), {"email": email})
            user_id, password_hash = row.one()

            # Never plaintext.
            assert password_hash != "a-real-bootstrap-password"
            # Genuinely a working bcrypt hash of the supplied password, not a placeholder.
            assert verify_password("a-real-bootstrap-password", password_hash) is True
            assert verify_password("a-different-password", password_hash) is False

            role_row = await session.execute(
                text(
                    "SELECT r.name FROM roles r JOIN user_roles ur ON ur.role_id = r.id WHERE ur.user_id = :user_id"
                ),
                {"user_id": str(user_id)},
            )
            assigned_roles = [r[0] for r in role_row.all()]
            assert assigned_roles == ["admin"]
        finally:
            await _cleanup_test_users(session)


@pytest.mark.anyio
async def test_second_execution_is_idempotent_and_does_not_duplicate(_dispose_shared_engine_after_each_test):
    async with _prepared_session() as session:
        email = _unique_test_email()
        try:
            first = await bootstrap_admin_user(email=email, password="first-password")
            second = await bootstrap_admin_user(email=email, password="first-password")

            assert first == "Bootstrap admin created successfully."
            assert second == "Bootstrap admin already exists; no password change performed."

            count = await session.execute(text("SELECT COUNT(*) FROM users WHERE email = :email"), {"email": email})
            assert count.scalar_one() == 1

            role_count = await session.execute(text("SELECT COUNT(*) FROM roles WHERE name = 'admin'"))
            assert role_count.scalar_one() == 1
        finally:
            await _cleanup_test_users(session)


@pytest.mark.anyio
async def test_rerun_with_a_different_password_does_not_overwrite_the_original(_dispose_shared_engine_after_each_test):
    async with _prepared_session() as session:
        email = _unique_test_email()
        try:
            await bootstrap_admin_user(email=email, password="original-password")
            second_message = await bootstrap_admin_user(email=email, password="a-completely-different-password")

            assert second_message == "Bootstrap admin already exists; no password change performed."

            row = await session.execute(text("SELECT password_hash FROM users WHERE email = :email"), {"email": email})
            password_hash = row.scalar_one()

            assert verify_password("original-password", password_hash) is True
            assert verify_password("a-completely-different-password", password_hash) is False
        finally:
            await _cleanup_test_users(session)


@pytest.mark.anyio
async def test_missing_email_fails_safely_without_mutating_the_database(_dispose_shared_engine_after_each_test):
    async with _prepared_session() as session:
        before = await session.execute(text("SELECT COUNT(*) FROM users"))
        before_count = before.scalar_one()

        with pytest.raises(BootstrapConfigurationError, match="BOOTSTRAP_ADMIN_EMAIL"):
            await bootstrap_admin_user(email="", password="some-password")

        after = await session.execute(text("SELECT COUNT(*) FROM users"))
        assert after.scalar_one() == before_count


@pytest.mark.anyio
async def test_missing_password_fails_safely_without_mutating_the_database(_dispose_shared_engine_after_each_test):
    async with _prepared_session() as session:
        before = await session.execute(text("SELECT COUNT(*) FROM users"))
        before_count = before.scalar_one()

        with pytest.raises(BootstrapConfigurationError, match="BOOTSTRAP_ADMIN_PASSWORD"):
            await bootstrap_admin_user(email=_unique_test_email(), password="")

        after = await session.execute(text("SELECT COUNT(*) FROM users"))
        assert after.scalar_one() == before_count


@pytest.mark.anyio
async def test_missing_admin_role_fails_safely_without_mutating_the_database(_dispose_shared_engine_after_each_test):
    async with _prepared_session() as session:
        # Simulate a database that has run some, but not all, migrations
        # (the `admin` role not yet seeded) by removing it temporarily.
        await session.execute(text("DELETE FROM roles WHERE name = 'admin'"))
        await session.commit()
        try:
            before = await session.execute(text("SELECT COUNT(*) FROM users"))
            before_count = before.scalar_one()

            with pytest.raises(BootstrapRoleMissingError, match="admin"):
                await bootstrap_admin_user(email=_unique_test_email(), password="some-password")

            after = await session.execute(text("SELECT COUNT(*) FROM users"))
            assert after.scalar_one() == before_count
        finally:
            # Restore the role so other tests (and a real dev database)
            # are never left missing a canonical role this suite didn't
            # own removing permanently.
            existing = await session.execute(text("SELECT id FROM roles WHERE name = 'admin'"))
            if existing.scalar_one_or_none() is None:
                await session.execute(
                    text("INSERT INTO roles (id, name, description) VALUES (:id, 'admin', 'test-restored admin role')"),
                    {"id": str(uuid.uuid4())},
                )
                await session.commit()


def test_no_public_registration_route_exists_on_the_gateway_app():
    paths = {route.path for route in gateway_app.routes}
    assert not any("register" in path for path in paths)


def test_bootstrap_is_not_invoked_by_ordinary_application_startup():
    """
    Static guard: `gateway_service/app/main.py` must never import or call
    the bootstrap module -- bootstrap is exclusively an operator-invoked
    script, never an application-startup side effect.
    """
    import inspect

    from backend.services.gateway_service.app import main as gateway_main

    source = inspect.getsource(gateway_main)
    assert "bootstrap_admin_user" not in source
    assert "bootstrap" not in source.lower()
