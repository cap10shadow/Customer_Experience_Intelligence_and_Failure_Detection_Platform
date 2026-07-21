import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from backend.services.root_cause_service.app.dependencies.services import get_root_cause_application_service
from backend.services.root_cause_service.app.main import app
from backend.services.root_cause_service.app.services.exceptions import (
    IncidentNotFoundError,
    InvalidLifecycleTransitionError,
    RefreshNotAllowedError,
    RootCauseAlreadyExistsError,
    RootCauseNotFoundError,
)
from backend.shared.constants.enums.root_cause import RootCause as RootCauseEnum
from backend.shared.constants.enums.root_cause import RootCauseStatus

EXISTING_INCIDENT_ID = uuid.uuid4()
MISSING_INCIDENT_ID = uuid.uuid4()
CONFLICTING_INCIDENT_ID = uuid.uuid4()
SAMPLE_ROOT_CAUSE_ID = uuid.uuid4()
MISSING_ROOT_CAUSE_ID = uuid.uuid4()
CONFIRMED_ROOT_CAUSE_ID = uuid.uuid4()
REJECTED_ROOT_CAUSE_ID = uuid.uuid4()


class _StubRootCause:
    """Plain object with the same attributes RootCauseResponse.model_validate reads."""

    def __init__(self, incident_id):
        self.id = SAMPLE_ROOT_CAUSE_ID
        self.incident_id = incident_id
        self.cause = RootCauseEnum.PAYMENT_GATEWAY_FAILURE
        self.confidence_score = 85
        self.confidence_level = "High"
        self.evidence = [{"type": "category", "description": "Payment complaints increased", "weight": 40}]
        self.explanation = "payment_gateway_failure identified with 85 confidence (High)."
        self.rule_version = "1.0"
        self.status = RootCauseStatus.IDENTIFIED
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


class MockRootCauseApplicationService:
    async def create_root_cause(self, incident_id):
        if incident_id == MISSING_INCIDENT_ID:
            raise IncidentNotFoundError(incident_id)
        if incident_id == CONFLICTING_INCIDENT_ID:
            raise RootCauseAlreadyExistsError(incident_id)
        return _StubRootCause(incident_id)

    async def get_root_cause(self, root_cause_id):
        if root_cause_id == SAMPLE_ROOT_CAUSE_ID:
            return _StubRootCause(EXISTING_INCIDENT_ID)
        return None

    async def get_root_cause_by_incident(self, incident_id):
        if incident_id == EXISTING_INCIDENT_ID:
            return _StubRootCause(incident_id)
        return None

    async def list_root_causes(self):
        return [_StubRootCause(EXISTING_INCIDENT_ID)]

    async def confirm_root_cause(self, root_cause_id):
        if root_cause_id == MISSING_ROOT_CAUSE_ID:
            raise RootCauseNotFoundError(root_cause_id)
        if root_cause_id == REJECTED_ROOT_CAUSE_ID:
            raise InvalidLifecycleTransitionError(RootCauseStatus.REJECTED, RootCauseStatus.CONFIRMED)
        stub = _StubRootCause(EXISTING_INCIDENT_ID)
        stub.id = root_cause_id
        stub.status = RootCauseStatus.CONFIRMED
        return stub

    async def reject_root_cause(self, root_cause_id):
        if root_cause_id == MISSING_ROOT_CAUSE_ID:
            raise RootCauseNotFoundError(root_cause_id)
        if root_cause_id == CONFIRMED_ROOT_CAUSE_ID:
            raise InvalidLifecycleTransitionError(RootCauseStatus.CONFIRMED, RootCauseStatus.REJECTED)
        stub = _StubRootCause(EXISTING_INCIDENT_ID)
        stub.id = root_cause_id
        stub.status = RootCauseStatus.REJECTED
        return stub

    async def refresh_root_cause(self, root_cause_id):
        if root_cause_id == MISSING_ROOT_CAUSE_ID:
            raise RootCauseNotFoundError(root_cause_id)
        if root_cause_id == CONFIRMED_ROOT_CAUSE_ID:
            raise RefreshNotAllowedError(RootCauseStatus.CONFIRMED)
        if root_cause_id == REJECTED_ROOT_CAUSE_ID:
            raise RefreshNotAllowedError(RootCauseStatus.REJECTED)
        stub = _StubRootCause(EXISTING_INCIDENT_ID)
        stub.id = root_cause_id
        return stub


@pytest.fixture
def override_dependencies():
    app.dependency_overrides[get_root_cause_application_service] = lambda: MockRootCauseApplicationService()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_post_root_causes_returns_201(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/root-causes", json={"incident_id": str(EXISTING_INCIDENT_ID)})
        assert response.status_code == 201
        body = response.json()
        assert body["cause"] == "payment_gateway_failure"
        assert body["incident_id"] == str(EXISTING_INCIDENT_ID)


@pytest.mark.anyio
async def test_post_root_causes_returns_404_when_incident_missing(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/root-causes", json={"incident_id": str(MISSING_INCIDENT_ID)})
        assert response.status_code == 404


@pytest.mark.anyio
async def test_post_root_causes_returns_409_when_already_exists(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/root-causes", json={"incident_id": str(CONFLICTING_INCIDENT_ID)})
        assert response.status_code == 409


@pytest.mark.anyio
async def test_get_root_cause_by_id(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/v1/root-causes/{SAMPLE_ROOT_CAUSE_ID}")
        assert response.status_code == 200
        assert response.json()["id"] == str(SAMPLE_ROOT_CAUSE_ID)


@pytest.mark.anyio
async def test_get_root_cause_by_id_404_when_missing(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/v1/root-causes/{uuid.uuid4()}")
        assert response.status_code == 404


@pytest.mark.anyio
async def test_list_root_causes(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/root-causes")
        assert response.status_code == 200
        assert len(response.json()) == 1


@pytest.mark.anyio
async def test_get_root_cause_by_incident(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/v1/incidents/{EXISTING_INCIDENT_ID}/root-cause")
        assert response.status_code == 200
        assert response.json()["incident_id"] == str(EXISTING_INCIDENT_ID)


@pytest.mark.anyio
async def test_get_root_cause_by_incident_404_when_missing(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/v1/incidents/{uuid.uuid4()}/root-cause")
        assert response.status_code == 404


# ------------------------------------------------------------------
# Phase 6 Step 3: lifecycle endpoints
# ------------------------------------------------------------------

@pytest.mark.anyio
async def test_confirm_returns_200(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.patch(f"/api/v1/root-causes/{SAMPLE_ROOT_CAUSE_ID}/confirm")
        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"


@pytest.mark.anyio
async def test_confirm_returns_404_when_missing(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.patch(f"/api/v1/root-causes/{MISSING_ROOT_CAUSE_ID}/confirm")
        assert response.status_code == 404


@pytest.mark.anyio
async def test_confirm_returns_409_when_rejected(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.patch(f"/api/v1/root-causes/{REJECTED_ROOT_CAUSE_ID}/confirm")
        assert response.status_code == 409


@pytest.mark.anyio
async def test_reject_returns_200(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.patch(f"/api/v1/root-causes/{SAMPLE_ROOT_CAUSE_ID}/reject")
        assert response.status_code == 200
        assert response.json()["status"] == "rejected"


@pytest.mark.anyio
async def test_reject_returns_404_when_missing(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.patch(f"/api/v1/root-causes/{MISSING_ROOT_CAUSE_ID}/reject")
        assert response.status_code == 404


@pytest.mark.anyio
async def test_reject_returns_409_when_confirmed(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.patch(f"/api/v1/root-causes/{CONFIRMED_ROOT_CAUSE_ID}/reject")
        assert response.status_code == 409


@pytest.mark.anyio
async def test_refresh_returns_200(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"/api/v1/root-causes/{SAMPLE_ROOT_CAUSE_ID}/refresh")
        assert response.status_code == 200


@pytest.mark.anyio
async def test_refresh_returns_404_when_missing(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"/api/v1/root-causes/{MISSING_ROOT_CAUSE_ID}/refresh")
        assert response.status_code == 404


@pytest.mark.anyio
async def test_refresh_returns_409_when_confirmed(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"/api/v1/root-causes/{CONFIRMED_ROOT_CAUSE_ID}/refresh")
        assert response.status_code == 409


@pytest.mark.anyio
async def test_refresh_returns_409_when_rejected(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"/api/v1/root-causes/{REJECTED_ROOT_CAUSE_ID}/refresh")
        assert response.status_code == 409
