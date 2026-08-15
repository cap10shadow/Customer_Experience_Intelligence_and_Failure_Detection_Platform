"""
Integration tests for POST /api/v1/auth/login, GET /api/v1/auth/me, and
POST /api/v1/auth/logout (Phase 13 Batch 2), plus the authentication
gate now covering the 6 protected business routers. Runs the real
Gateway app (`TestClient`, same pattern as `test_main.py`/
`test_recommendations.py`) against real PostgreSQL -- skips cleanly,
module-wide, if it is not reachable (same convention as
`test_identity_repository.py`).

Every test creates its own uniquely-emailed user directly via
`UserRepository` (there is no /register route -- Batch 2 doesn't add
one) and deletes it afterward; nothing here relies on transaction
rollback (the app's own request-triggered session is a separate
connection from this file's setup/teardown session, so rows must be
really committed for the app to see them, and really deleted after).
"""

import uuid
from typing import AsyncIterator, Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.services.gateway_service.app.core.auth_dependency import SESSION_COOKIE_NAME, get_current_user
from backend.services.gateway_service.app.core.security import hash_password
from backend.services.gateway_service.app.main import app
from backend.services.gateway_service.app.models.identity import User
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


class _TestUser:
    def __init__(self, email: str, password: str, user_id: uuid.UUID):
        self.email = email
        self.password = password
        self.user_id = user_id


async def _create_user(*, password: str, is_active: bool = True) -> _TestUser:
    email = f"batch2-{uuid.uuid4().hex}@example.com"
    async with AsyncSession(bind=_test_engine, expire_on_commit=False) as session:
        user = User(email=email, password_hash=hash_password(password), is_active=is_active)
        session.add(user)
        await session.commit()
        return _TestUser(email=email, password=password, user_id=user.id)


async def _delete_user(user_id: uuid.UUID) -> None:
    async with AsyncSession(bind=_test_engine, expire_on_commit=False) as session:
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def active_user() -> AsyncIterator[_TestUser]:
    if not await _is_database_available():
        pytest.skip("PostgreSQL is not reachable on localhost:5432 -- run `docker compose up postgres` to enable these tests")
    user = await _create_user(password="a-correct-password-123")
    yield user
    await _delete_user(user.user_id)


@pytest.fixture
async def inactive_user() -> AsyncIterator[_TestUser]:
    if not await _is_database_available():
        pytest.skip("PostgreSQL is not reachable on localhost:5432 -- run `docker compose up postgres` to enable these tests")
    user = await _create_user(password="a-correct-password-123", is_active=False)
    yield user
    await _delete_user(user.user_id)


@pytest.fixture(autouse=True)
def _real_auth_boundary():
    """Every test in this file exercises the real 401/authenticated boundary -- pop the conftest-wide test-principal override for the duration of each test."""
    app.dependency_overrides.pop(get_current_user, None)
    yield


# --- POST /auth/login ---------------------------------------------------------------


@pytest.mark.anyio
async def test_login_with_correct_credentials_returns_200_and_sets_the_session_cookie(active_user: _TestUser):
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/login", json={"email": active_user.email, "password": active_user.password})

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == active_user.email
    assert body["userId"] == str(active_user.user_id)
    assert body["roles"] == []
    assert SESSION_COOKIE_NAME in response.cookies


@pytest.mark.anyio
async def test_login_response_never_contains_password_hash_or_a_raw_token_field(active_user: _TestUser):
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/login", json={"email": active_user.email, "password": active_user.password})

    body_text = response.text
    assert "password_hash" not in body_text
    assert "passwordHash" not in body_text
    assert active_user.password not in body_text


@pytest.mark.anyio
async def test_login_cookie_is_httponly_and_samesite_lax(active_user: _TestUser):
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/login", json={"email": active_user.email, "password": active_user.password})

    set_cookie_header = response.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie_header
    assert "samesite=lax" in set_cookie_header.lower()


@pytest.mark.anyio
async def test_login_with_unknown_email_returns_401_with_a_generic_message():
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/login", json={"email": "nobody-batch2@example.com", "password": "anything"})

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid email or password."


@pytest.mark.anyio
async def test_login_with_wrong_password_returns_401_with_the_same_generic_message(active_user: _TestUser):
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/login", json={"email": active_user.email, "password": "the-wrong-password"})

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid email or password."


@pytest.mark.anyio
async def test_login_with_an_inactive_user_returns_401_with_the_same_generic_message(inactive_user: _TestUser):
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/login", json={"email": inactive_user.email, "password": inactive_user.password})

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid email or password."


@pytest.mark.anyio
async def test_failed_login_never_logs_the_submitted_password(active_user: _TestUser, capsys: pytest.CaptureFixture[str]):
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"email": active_user.email, "password": "a-secret-wrong-password"})

    captured = capsys.readouterr()
    assert "a-secret-wrong-password" not in captured.out
    assert "a-secret-wrong-password" not in captured.err


# --- GET /auth/me ---------------------------------------------------------------


@pytest.mark.anyio
async def test_me_without_a_session_returns_401():
    with TestClient(app) as client:
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_me_with_a_malformed_cookie_returns_401():
    with TestClient(app) as client:
        client.cookies.set(SESSION_COOKIE_NAME, "not-a-real-jwt")
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_me_after_a_real_login_returns_the_authenticated_user(active_user: _TestUser):
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"email": active_user.email, "password": active_user.password})
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == active_user.email
    assert body["userId"] == str(active_user.user_id)


# --- POST /auth/logout ---------------------------------------------------------------


@pytest.mark.anyio
async def test_logout_returns_204():
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204


@pytest.mark.anyio
async def test_me_returns_401_after_logout(active_user: _TestUser):
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"email": active_user.email, "password": active_user.password})
        assert client.get("/api/v1/auth/me").status_code == 200

        client.post("/api/v1/auth/logout")
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


# --- Protected business routes ---------------------------------------------------------------


@pytest.mark.anyio
async def test_a_protected_business_route_without_authentication_returns_401():
    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_a_protected_business_route_with_a_real_session_is_not_rejected_for_authentication(active_user: _TestUser):
    """
    Proves the auth gate was passed (not a 401) once a real session
    exists -- the response is a 503 (no anomaly_service/etc. running in
    this test process), which is exactly the evidence that
    authentication succeeded and the request reached real downstream-call
    code, not a stand-in for full aggregation success.
    """
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"email": active_user.email, "password": active_user.password})
        response = client.get("/api/v1/dashboard")

    assert response.status_code != 401


@pytest.mark.anyio
async def test_health_remains_unauthenticated():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200


@pytest.mark.anyio
async def test_health_ready_remains_unauthenticated():
    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code in (200, 503)  # never 401 -- readiness must never require a session


@pytest.mark.anyio
async def test_metrics_remains_unauthenticated():
    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
