import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from backend.services.anomaly_service.app.main import app
from backend.services.anomaly_service.app.dependencies.services import get_correlation_engine
from backend.services.anomaly_service.app.schemas.anomalies import ActiveAnomalyResponse
from backend.services.anomaly_service.app.schemas.incidents import IncidentResponse, IncidentRunItem, IncidentRunResult
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyStatus, AnomalyType
from backend.shared.constants.enums.incident import IncidentStatus

SAMPLE_ID = uuid.uuid4()


def _sample_incident():
    return IncidentResponse(
        id=SAMPLE_ID,
        incident_key="INC-ABCD1234",
        title="South Regional Incident",
        severity=AnomalySeverity.CRITICAL,
        status=IncidentStatus.OPEN,
        confidence_score=55,
        summary="2 correlated anomalies. Confidence: 55 (Possible). Reasons: Same severity (critical).",
        started_at="2026-07-20T00:00:00Z",
        last_updated_at="2026-07-20T00:00:00Z",
        resolved_at=None,
    )


def _sample_anomaly():
    return ActiveAnomalyResponse(
        id=uuid.uuid4(),
        fingerprint="complaint_spike:global:ALL",
        type=AnomalyType.COMPLAINT_SPIKE,
        severity=AnomalySeverity.CRITICAL,
        entity_type="global",
        entity_value=None,
        baseline_value=10,
        current_value=30,
        percentage_change=200.0,
        triggered_rule="test",
        explanation="test",
        first_detected_at="2026-07-20T00:00:00Z",
        last_seen_at="2026-07-20T00:00:00Z",
        status=AnomalyStatus.ACTIVE,
    )


class MockCorrelationEngine:
    async def run(self, window_minutes):
        incident = _sample_incident()
        return IncidentRunResult(
            run_at="2026-07-20T00:00:00Z",
            created=[IncidentRunItem(incident=incident, linked_anomaly_count=2, reason="New incident correlated from 2 anomalies.")],
        )

    async def get_active(self):
        return [_sample_incident()]

    async def get_by_id(self, incident_id):
        if incident_id == SAMPLE_ID:
            return _sample_incident()
        return None

    async def get_anomalies_for_incident(self, incident_id):
        if incident_id == SAMPLE_ID:
            return [_sample_anomaly(), _sample_anomaly()]
        return None


@pytest.fixture
def override_dependencies():
    app.dependency_overrides[get_correlation_engine] = lambda: MockCorrelationEngine()
    yield
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_post_run_returns_200_with_results(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/incidents/run?window_minutes=15")
        assert response.status_code == 200
        body = response.json()
        assert len(body["created"]) == 1
        assert body["created"][0]["linked_anomaly_count"] == 2


@pytest.mark.anyio
async def test_get_incidents_returns_active_list(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/incidents")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["status"] == "open"


@pytest.mark.anyio
async def test_get_incident_by_id(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/v1/incidents/{SAMPLE_ID}")
        assert response.status_code == 200
        assert response.json()["id"] == str(SAMPLE_ID)


@pytest.mark.anyio
async def test_get_incident_by_id_404_when_missing(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/v1/incidents/{uuid.uuid4()}")
        assert response.status_code == 404


@pytest.mark.anyio
async def test_get_incident_anomalies(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/v1/incidents/{SAMPLE_ID}/anomalies")
        assert response.status_code == 200
        assert len(response.json()) == 2


@pytest.mark.anyio
async def test_get_incident_anomalies_404_when_incident_missing(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/v1/incidents/{uuid.uuid4()}/anomalies")
        assert response.status_code == 404
