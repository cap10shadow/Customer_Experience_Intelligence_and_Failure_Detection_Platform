"""
Integration tests for internal service-to-service authentication on
copilot_service's `POST /api/v1/copilot/messages` route (Phase 13
Batch 4, AD-5). Self-contained module-level setup (real Postgres,
skip-if-unavailable, mocked downstream `http_client`) mirroring
`test_copilot_api.py`'s own established convention exactly, so this
file behaves identically whether run standalone or alongside it.
"""

import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.services.copilot_service.app.dependencies.http_client import get_http_client
from backend.services.copilot_service.app.main import app
from backend.shared.config.settings import Settings, settings
from backend.shared.database.session import get_db_session
from backend.shared.security.internal_auth import INTERNAL_SECRET_HEADER

app.dependency_overrides[get_http_client] = lambda: httpx.AsyncClient(
    transport=httpx.MockTransport(lambda request: httpx.Response(404))
)

_test_settings = Settings(POSTGRES_HOST="localhost")
_test_engine = create_async_engine(_test_settings.database_url, poolclass=NullPool)
_test_session_maker = async_sessionmaker(_test_engine, expire_on_commit=False, autoflush=False)


async def _override_get_db_session():
    async with _test_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db_session] = _override_get_db_session


def _database_available() -> bool:
    async def _check() -> bool:
        try:
            async with _test_engine.connect() as probe:
                await probe.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    return asyncio.run(_check())


pytestmark = pytest.mark.skipif(
    not _database_available(),
    reason="PostgreSQL is not reachable on localhost:5432 -- run `docker compose up postgres` to enable these tests",
)

client = TestClient(app)


def test_copilot_message_without_secret_is_rejected():
    response = client.post("/api/v1/copilot/messages", json={"message": "hello"})

    assert response.status_code == 401


def test_copilot_message_with_wrong_secret_is_rejected():
    response = client.post(
        "/api/v1/copilot/messages", json={"message": "hello"}, headers={INTERNAL_SECRET_HEADER: "the-wrong-secret"}
    )

    assert response.status_code == 401


def test_copilot_message_with_the_correct_secret_is_accepted():
    response = client.post(
        "/api/v1/copilot/messages",
        json={"message": "hello"},
        headers={INTERNAL_SECRET_HEADER: settings.INTERNAL_SERVICE_SECRET},
    )

    assert response.status_code == 200


def test_the_401_body_never_contains_the_configured_secret():
    response = client.post("/api/v1/copilot/messages", json={"message": "hello"})

    assert settings.INTERNAL_SERVICE_SECRET not in response.text
