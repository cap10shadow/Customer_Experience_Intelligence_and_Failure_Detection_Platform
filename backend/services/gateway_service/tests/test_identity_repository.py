"""
Repository/model tests: exercise `UserRepository`/`RoleRepository`
against a real PostgreSQL database (no mocking of SQL execution) --
the only way to genuinely verify uniqueness constraints, foreign key
integrity, and real save/query behavior (Phase 13 Batch 1, AD-1).
Connects to `localhost:5432` (the same Postgres `docker compose up
postgres` exposes) and skips cleanly, module-wide, if it is not
reachable -- `python -m pytest backend` remains green with or without
Docker running (same convention as
`copilot_service/tests/test_conversation_persistence_repository.py`).

Every test runs inside a transaction that is always rolled back at the
end, so no test data is ever actually committed or left behind.
"""

import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.services.gateway_service.app.core.security import hash_password, verify_password
from backend.services.gateway_service.app.models.identity import Role, User, UserRole
from backend.services.gateway_service.app.repositories.identity_repository import RoleRepository, UserRepository
from backend.shared.config.settings import Settings

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
async def _repository_session() -> AsyncIterator[AsyncSession]:
    if not await _is_database_available():
        pytest.skip("PostgreSQL is not reachable on localhost:5432 -- run `docker compose up postgres` to enable these tests")

    async with _test_engine.connect() as conn:
        await conn.run_sync(lambda sync_conn: User.__table__.create(sync_conn, checkfirst=True))  # type: ignore[attr-defined]
        await conn.run_sync(lambda sync_conn: Role.__table__.create(sync_conn, checkfirst=True))  # type: ignore[attr-defined]
        await conn.run_sync(lambda sync_conn: UserRole.__table__.create(sync_conn, checkfirst=True))  # type: ignore[attr-defined]
        await conn.commit()

        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest.fixture
def anyio_backend():
    return "asyncio"


# --- User model / UserRepository --------------------------------------------------


@pytest.mark.anyio
async def test_create_persists_a_user_with_a_hashed_password():
    async with _repository_session() as session:
        repository = UserRepository(session)
        hashed = hash_password("a-real-password")

        created = await repository.create(email="alice@example.com", password_hash=hashed)

        assert created.id is not None
        assert created.email == "alice@example.com"
        assert created.password_hash == hashed
        assert created.password_hash != "a-real-password"
        assert created.is_active is True
        assert created.last_login_at is None


@pytest.mark.anyio
async def test_get_by_email_retrieves_a_saved_user():
    async with _repository_session() as session:
        repository = UserRepository(session)
        await repository.create(email="bob@example.com", password_hash=hash_password("x"))

        fetched = await repository.get_by_email("bob@example.com")

        assert fetched is not None
        assert fetched.email == "bob@example.com"


@pytest.mark.anyio
async def test_get_by_id_retrieves_a_saved_user():
    async with _repository_session() as session:
        repository = UserRepository(session)
        created = await repository.create(email="carol@example.com", password_hash=hash_password("x"))

        fetched = await repository.get_by_id(created.id)

        assert fetched is not None
        assert fetched.id == created.id


@pytest.mark.anyio
async def test_get_by_email_returns_none_for_unknown_email():
    async with _repository_session() as session:
        repository = UserRepository(session)

        assert await repository.get_by_email("nobody@example.com") is None


@pytest.mark.anyio
async def test_duplicate_email_is_rejected_by_the_database():
    async with _repository_session() as session:
        repository = UserRepository(session)
        await repository.create(email="dupe@example.com", password_hash=hash_password("x"))

        with pytest.raises(IntegrityError):
            await repository.create(email="dupe@example.com", password_hash=hash_password("y"))


@pytest.mark.anyio
async def test_end_to_end_hash_and_verify_through_persistence():
    """A user created with a hashed password can be verified against the persisted hash after a round trip."""
    async with _repository_session() as session:
        repository = UserRepository(session)
        password = "correct horse battery staple"
        created = await repository.create(email="dave@example.com", password_hash=hash_password(password))

        fetched = await repository.get_by_id(created.id)

        assert fetched is not None
        assert verify_password(password, fetched.password_hash) is True
        assert verify_password("wrong-password", fetched.password_hash) is False


# --- Role model / RoleRepository ----------------------------------------------------


@pytest.mark.anyio
async def test_create_persists_a_role():
    async with _repository_session() as session:
        repository = RoleRepository(session)

        created = await repository.create(name="viewer-test", description="read-only access")

        assert created.id is not None
        assert created.name == "viewer-test"
        assert created.description == "read-only access"


@pytest.mark.anyio
async def test_get_by_name_retrieves_a_saved_role():
    async with _repository_session() as session:
        repository = RoleRepository(session)
        await repository.create(name="operator-test")

        fetched = await repository.get_by_name("operator-test")

        assert fetched is not None
        assert fetched.name == "operator-test"


@pytest.mark.anyio
async def test_duplicate_role_name_is_rejected_by_the_database():
    async with _repository_session() as session:
        repository = RoleRepository(session)
        await repository.create(name="admin-test")

        with pytest.raises(IntegrityError):
            await repository.create(name="admin-test")


# --- user_roles relationship --------------------------------------------------------


@pytest.mark.anyio
async def test_assign_to_user_creates_the_relationship():
    async with _repository_session() as session:
        user_repository = UserRepository(session)
        role_repository = RoleRepository(session)
        user = await user_repository.create(email="erin@example.com", password_hash=hash_password("x"))
        role = await role_repository.create(name="erin-role")

        await role_repository.assign_to_user(user_id=user.id, role_id=role.id)
        roles = await role_repository.list_for_user(user.id)

        assert [r.name for r in roles] == ["erin-role"]


@pytest.mark.anyio
async def test_list_for_user_is_empty_when_no_role_is_assigned():
    async with _repository_session() as session:
        user_repository = UserRepository(session)
        user = await user_repository.create(email="frank@example.com", password_hash=hash_password("x"))

        assert await RoleRepository(session).list_for_user(user.id) == []


@pytest.mark.anyio
async def test_duplicate_user_role_assignment_is_rejected_by_the_database():
    async with _repository_session() as session:
        user_repository = UserRepository(session)
        role_repository = RoleRepository(session)
        user = await user_repository.create(email="grace@example.com", password_hash=hash_password("x"))
        role = await role_repository.create(name="grace-role")
        await role_repository.assign_to_user(user_id=user.id, role_id=role.id)

        with pytest.raises(IntegrityError):
            await role_repository.assign_to_user(user_id=user.id, role_id=role.id)


@pytest.mark.anyio
async def test_assign_to_user_with_unknown_user_id_violates_the_foreign_key():
    async with _repository_session() as session:
        role_repository = RoleRepository(session)
        role = await role_repository.create(name="orphan-role")

        with pytest.raises(IntegrityError):
            await role_repository.assign_to_user(user_id=uuid.uuid4(), role_id=role.id)
