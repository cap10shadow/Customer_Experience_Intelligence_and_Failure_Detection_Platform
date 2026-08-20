"""
Integration tests for the real role-based authorization boundary
(Phase 13 Batch 3, §11/§12's permission matrix). Runs the real Gateway
app (`TestClient`, same pattern as `test_auth_api.py`) against real
PostgreSQL, using the seeded `viewer`/`operator`/`admin` role rows
(migration `12fef1ff2286`) -- skips cleanly, module-wide, if Postgres
is not reachable.

Every test creates its own uniquely-emailed user (and, where needed, a
real `user_roles` row against a real seeded role) directly via
`UserRepository`/`RoleRepository`, logs in through the real
`POST /auth/login` route to obtain a real cookie (never fabricates a
JWT by hand), and deletes what it created afterward.
"""

import uuid
from typing import AsyncIterator, Optional, Sequence

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.services.gateway_service.app.core.auth_dependency import get_current_user
from backend.services.gateway_service.app.core.security import hash_password
from backend.services.gateway_service.app.main import app
from backend.services.gateway_service.app.models.identity import Role, User, UserRole
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


async def _create_user_with_roles(*, roles: Sequence[str]) -> _TestUser:
    email = f"rbac-{uuid.uuid4().hex}@example.com"
    password = "a-correct-password-123"
    async with AsyncSession(bind=_test_engine, expire_on_commit=False) as session:
        user = User(email=email, password_hash=hash_password(password), is_active=True)
        session.add(user)
        await session.flush()

        for role_name in roles:
            role = (await session.execute(select(Role).where(Role.name == role_name))).scalar_one()
            session.add(UserRole(user_id=user.id, role_id=role.id))

        await session.commit()
        return _TestUser(email=email, password=password, user_id=user.id)


async def _delete_user(user_id: uuid.UUID) -> None:
    async with AsyncSession(bind=_test_engine, expire_on_commit=False) as session:
        await session.execute(delete(UserRole).where(UserRole.user_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _user_fixture(roles: Sequence[str]):
    @pytest.fixture
    async def _fixture() -> AsyncIterator[_TestUser]:
        if not await _is_database_available():
            pytest.skip("PostgreSQL is not reachable on localhost:5432 -- run `docker compose up postgres` to enable these tests")
        user = await _create_user_with_roles(roles=roles)
        yield user
        await _delete_user(user.user_id)

    return _fixture


viewer_user = _user_fixture(["viewer"])
operator_user = _user_fixture(["operator"])
admin_user = _user_fixture(["admin"])
roleless_user = _user_fixture([])


@pytest.fixture(autouse=True)
def _real_auth_boundary():
    """Every test in this file exercises the real 401/403/200 boundary -- pop the conftest-wide test-principal override for the duration of each test."""
    app.dependency_overrides.pop(get_current_user, None)


def _login(client: TestClient, user: _TestUser) -> None:
    response = client.post("/api/v1/auth/login", json={"email": user.email, "password": user.password})
    assert response.status_code == 200


# --- Seeded roles exist -------------------------------------------------------------


@pytest.mark.anyio
async def test_the_three_canonical_roles_are_seeded_in_the_database():
    if not await _is_database_available():
        pytest.skip("PostgreSQL is not reachable on localhost:5432 -- run `docker compose up postgres` to enable these tests")
    async with AsyncSession(bind=_test_engine, expire_on_commit=False) as session:
        names = set((await session.execute(select(Role.name))).scalars().all())

    assert {"viewer", "operator", "admin"}.issubset(names)


# --- Anonymous / authentication (unaffected by RBAC) --------------------------------


@pytest.mark.anyio
async def test_anonymous_request_to_a_viewer_route_is_401_not_403():
    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_anonymous_request_to_an_operator_route_is_401_not_403():
    with TestClient(app) as client:
        response = client.patch("/api/v1/recommendations/does-not-matter/decision", json={"decision": "approved"})

    assert response.status_code == 401


# --- Viewer-level route (GET /dashboard) ---------------------------------------------


@pytest.mark.anyio
async def test_authenticated_user_with_no_roles_gets_403_on_a_viewer_route(roleless_user: _TestUser):
    with TestClient(app) as client:
        _login(client, roleless_user)
        response = client.get("/api/v1/dashboard")

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "FORBIDDEN"


@pytest.mark.anyio
async def test_viewer_passes_the_authorization_gate_on_a_viewer_route(viewer_user: _TestUser):
    with TestClient(app) as client:
        _login(client, viewer_user)
        response = client.get("/api/v1/dashboard")

    assert response.status_code != 401
    assert response.status_code != 403


@pytest.mark.anyio
async def test_operator_also_passes_a_viewer_route_since_operator_implies_viewer(operator_user: _TestUser):
    with TestClient(app) as client:
        _login(client, operator_user)
        response = client.get("/api/v1/dashboard")

    assert response.status_code != 401
    assert response.status_code != 403


# --- Operator-level route (PATCH .../decision) ----------------------------------------


@pytest.mark.anyio
async def test_viewer_only_gets_403_on_the_operator_only_decision_route(viewer_user: _TestUser):
    with TestClient(app) as client:
        _login(client, viewer_user)
        response = client.patch(
            "/api/v1/recommendations/00000000-0000-0000-0000-000000000000/decision", json={"decision": "approved"}
        )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_operator_passes_the_authorization_gate_on_the_decision_route(operator_user: _TestUser):
    with TestClient(app) as client:
        _login(client, operator_user)
        response = client.patch(
            "/api/v1/recommendations/00000000-0000-0000-0000-000000000000/decision", json={"decision": "approved"}
        )

    assert response.status_code != 401
    assert response.status_code != 403


@pytest.mark.anyio
async def test_admin_also_passes_the_decision_route_since_admin_implies_operator(admin_user: _TestUser):
    with TestClient(app) as client:
        _login(client, admin_user)
        response = client.patch(
            "/api/v1/recommendations/00000000-0000-0000-0000-000000000000/decision", json={"decision": "approved"}
        )

    assert response.status_code != 401
    assert response.status_code != 403


# --- Operator-level route (POST /copilot/messages) ------------------------------------


@pytest.mark.anyio
async def test_viewer_only_gets_403_on_the_operator_only_copilot_route(viewer_user: _TestUser):
    with TestClient(app) as client:
        _login(client, viewer_user)
        response = client.post("/api/v1/copilot/messages", json={"message": "hello"})

    assert response.status_code == 403


@pytest.mark.anyio
async def test_operator_passes_the_authorization_gate_on_the_copilot_route(operator_user: _TestUser):
    with TestClient(app) as client:
        _login(client, operator_user)
        response = client.post("/api/v1/copilot/messages", json={"message": "hello"})

    assert response.status_code != 401
    assert response.status_code != 403


# --- Operator-level route (DELETE /copilot/conversations/{id}, Phase 13 Batch 6) ------


@pytest.mark.anyio
async def test_viewer_only_gets_403_on_the_operator_only_copilot_delete_route(viewer_user: _TestUser):
    with TestClient(app) as client:
        _login(client, viewer_user)
        response = client.delete(f"/api/v1/copilot/conversations/{uuid.uuid4()}")

    assert response.status_code == 403


@pytest.mark.anyio
async def test_operator_passes_the_authorization_gate_on_the_copilot_delete_route(operator_user: _TestUser):
    with TestClient(app) as client:
        _login(client, operator_user)
        response = client.delete(f"/api/v1/copilot/conversations/{uuid.uuid4()}")

    assert response.status_code != 401
    assert response.status_code != 403


# --- Operator-level route (POST /ingestion/complaints) ---------------------------------


@pytest.mark.anyio
async def test_viewer_only_gets_403_on_the_operator_only_ingestion_route(viewer_user: _TestUser):
    with TestClient(app) as client:
        _login(client, viewer_user)
        response = client.post("/api/v1/ingestion/complaints", json={"complaint_text": "a" * 20})

    assert response.status_code == 403


@pytest.mark.anyio
async def test_operator_passes_the_authorization_gate_on_the_ingestion_route(operator_user: _TestUser):
    with TestClient(app) as client:
        _login(client, operator_user)
        response = client.post("/api/v1/ingestion/complaints", json={"complaint_text": "a" * 20})

    assert response.status_code != 401
    assert response.status_code != 403


@pytest.mark.anyio
async def test_viewer_passes_the_authorization_gate_on_the_ingestion_list_route(viewer_user: _TestUser):
    with TestClient(app) as client:
        _login(client, viewer_user)
        response = client.get("/api/v1/ingestion/complaints")

    assert response.status_code != 401
    assert response.status_code != 403


# --- Operator-level routes (root-cause confirm/reject/refresh) -------------------------


@pytest.mark.anyio
async def test_viewer_only_gets_403_on_the_operator_only_root_cause_confirm_route(viewer_user: _TestUser):
    with TestClient(app) as client:
        _login(client, viewer_user)
        response = client.patch("/api/v1/investigations/does-not-matter/root-cause/confirm")

    assert response.status_code == 403


@pytest.mark.anyio
async def test_operator_passes_the_authorization_gate_on_the_root_cause_confirm_route(operator_user: _TestUser):
    with TestClient(app) as client:
        _login(client, operator_user)
        response = client.patch("/api/v1/investigations/does-not-matter/root-cause/confirm")

    assert response.status_code != 401
    assert response.status_code != 403


# --- Client cannot elevate its own privileges -----------------------------------------


@pytest.mark.anyio
async def test_a_spoofed_role_header_does_not_grant_operator_access(viewer_user: _TestUser):
    with TestClient(app) as client:
        _login(client, viewer_user)
        response = client.patch(
            "/api/v1/recommendations/00000000-0000-0000-0000-000000000000/decision",
            json={"decision": "approved"},
            headers={"X-Role": "admin", "X-User-Roles": "admin,operator"},
        )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_a_spoofed_role_in_the_request_body_does_not_grant_operator_access(viewer_user: _TestUser):
    with TestClient(app) as client:
        _login(client, viewer_user)
        response = client.patch(
            "/api/v1/recommendations/00000000-0000-0000-0000-000000000000/decision",
            json={"decision": "approved", "role": "admin", "roles": ["admin"]},
        )

    assert response.status_code == 403


# --- /auth/me requires no specific role -----------------------------------------------


@pytest.mark.anyio
async def test_me_works_for_a_roleless_authenticated_user(roleless_user: _TestUser):
    with TestClient(app) as client:
        _login(client, roleless_user)
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 200


# --- Unauthenticated infrastructure endpoints remain unauthenticated -------------------


@pytest.mark.anyio
async def test_health_remains_unauthenticated_and_unauthorized():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200


@pytest.mark.anyio
async def test_health_ready_remains_unauthenticated_and_unauthorized():
    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code in (200, 503)


@pytest.mark.anyio
async def test_metrics_remains_unauthenticated_and_unauthorized():
    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
