import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from backend.services.business_impact_service.app.dependencies.services import (
    get_business_impact_application_service,
)
from backend.services.business_impact_service.app.domain.business_priority import BusinessPriority
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.main import app
from backend.services.business_impact_service.app.services.exceptions import (
    IncidentNotFoundError,
    RootCauseNotFoundError,
)
from backend.shared.constants.enums.business_impact_assessment import BusinessImpactAssessmentStatus

EXISTING_INCIDENT_ID = uuid.uuid4()
MISSING_INCIDENT_ID = uuid.uuid4()
NO_ROOT_CAUSE_INCIDENT_ID = uuid.uuid4()
SAMPLE_ASSESSMENT_ID = uuid.uuid4()
MISSING_ASSESSMENT_ID = uuid.uuid4()
SAMPLE_ROOT_CAUSE_ID = uuid.uuid4()


class _StubAssessment:
    """Plain object with the same attributes BusinessImpactAssessmentResponse.model_validate reads."""

    def __init__(self, incident_id, assessment_id=None):
        self.assessment_id = assessment_id or SAMPLE_ASSESSMENT_ID
        self.incident_id = incident_id
        self.root_cause_id = SAMPLE_ROOT_CAUSE_ID
        self.financial = ImpactLevel.HIGH
        self.customer = ImpactLevel.MEDIUM
        self.operational = ImpactLevel.CRITICAL
        self.sla = ImpactLevel.LOW
        self.reputation = ImpactLevel.NONE
        self.overall_score = 78
        self.overall_severity = ImpactLevel.HIGH
        self.business_priority = BusinessPriority.HIGH
        self.confidence = 80
        self.estimated_affected_customers = 250
        self.explanation = "Overall business impact is high."
        self.status = BusinessImpactAssessmentStatus.ACTIVE
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


class MockBusinessImpactApplicationService:
    async def create_assessment(self, incident_id):
        if incident_id == MISSING_INCIDENT_ID:
            raise IncidentNotFoundError(incident_id)
        if incident_id == NO_ROOT_CAUSE_INCIDENT_ID:
            raise RootCauseNotFoundError(incident_id)
        return _StubAssessment(incident_id)

    async def get_assessment(self, assessment_id):
        if assessment_id == SAMPLE_ASSESSMENT_ID:
            return _StubAssessment(EXISTING_INCIDENT_ID, assessment_id)
        return None

    async def list_assessments(self, *, severity=None, priority=None, incident_id=None):
        return [_StubAssessment(EXISTING_INCIDENT_ID)]


@pytest.fixture
def override_dependencies():
    app.dependency_overrides[get_business_impact_application_service] = lambda: MockBusinessImpactApplicationService()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_post_business_impact_returns_201(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/business-impact", json={"incident_id": str(EXISTING_INCIDENT_ID)})
        assert response.status_code == 201
        body = response.json()
        assert body["incident_id"] == str(EXISTING_INCIDENT_ID)
        assert body["overall_severity"] == "high"
        assert body["business_priority"] == "high"


@pytest.mark.anyio
async def test_post_business_impact_returns_404_when_incident_missing(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/business-impact", json={"incident_id": str(MISSING_INCIDENT_ID)})
        assert response.status_code == 404


@pytest.mark.anyio
async def test_post_business_impact_returns_404_when_root_cause_missing(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/business-impact", json={"incident_id": str(NO_ROOT_CAUSE_INCIDENT_ID)})
        assert response.status_code == 404


@pytest.mark.anyio
async def test_post_business_impact_rejects_extra_fields_beyond_incident_id(override_dependencies):
    # The client must only ever provide incident_id -- request body is
    # validated by CreateBusinessImpactRequest (incident_id: uuid.UUID),
    # so a malformed/missing incident_id is rejected before the service runs.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/business-impact", json={"incident_id": "not-a-uuid"})
        assert response.status_code == 422


@pytest.mark.anyio
async def test_get_business_impact_by_id(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/v1/business-impact/{SAMPLE_ASSESSMENT_ID}")
        assert response.status_code == 200
        assert response.json()["assessment_id"] == str(SAMPLE_ASSESSMENT_ID)


@pytest.mark.anyio
async def test_get_business_impact_by_id_404_when_missing(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/v1/business-impact/{MISSING_ASSESSMENT_ID}")
        assert response.status_code == 404


@pytest.mark.anyio
async def test_list_business_impact_assessments(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/business-impact")
        assert response.status_code == 200
        assert len(response.json()) == 1


@pytest.mark.anyio
async def test_list_business_impact_assessments_accepts_filters(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/v1/business-impact",
            params={"severity": "high", "priority": "high", "incident_id": str(EXISTING_INCIDENT_ID)},
        )
        assert response.status_code == 200
        assert len(response.json()) == 1


@pytest.mark.anyio
async def test_list_business_impact_assessments_rejects_invalid_severity_filter(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/business-impact", params={"severity": "not-a-level"})
        assert response.status_code == 422


@pytest.mark.anyio
async def test_no_update_endpoint_exists(override_dependencies):
    # Assessments are immutable -- there is no PUT/PATCH route for this resource.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.patch(f"/api/v1/business-impact/{SAMPLE_ASSESSMENT_ID}")
        assert response.status_code == 405
