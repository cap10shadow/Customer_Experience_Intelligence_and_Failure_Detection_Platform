import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from backend.services.anomaly_service.app.main import app
from backend.services.anomaly_service.app.dependencies.services import get_anomaly_engine
from backend.services.anomaly_service.app.schemas.anomalies import (
    ActiveAnomalyResponse,
    AnomalyRunItem,
    AnomalyRunResult,
)
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyStatus, AnomalyType

SAMPLE_ID = uuid.uuid4()


def _sample_anomaly(anomaly_id=SAMPLE_ID):
    return ActiveAnomalyResponse(
        id=anomaly_id,
        fingerprint="complaint_spike:global:ALL",
        type=AnomalyType.COMPLAINT_SPIKE,
        severity=AnomalySeverity.HIGH,
        entity_type="global",
        entity_value=None,
        baseline_value=10,
        current_value=30,
        percentage_change=200.0,
        triggered_rule="percentage_change magnitude 200.0% in (100%, 200%] -> HIGH",
        explanation="complaint_spike detected for global: baseline=10, current=30, change=+200.0%, severity=high.",
        first_detected_at="2026-07-19T00:00:00Z",
        last_seen_at="2026-07-19T00:00:00Z",
        status=AnomalyStatus.ACTIVE,
    )


class MockAnomalyEngine:
    async def run(self, days):
        anomaly = _sample_anomaly()
        return AnomalyRunResult(
            run_at="2026-07-19T00:00:00Z",
            period=f"Last {days} Days",
            detected=[AnomalyRunItem(anomaly=anomaly, reason="New anomaly detected.")],
            updated=[],
            resolved=[],
        )

    async def get_active(self):
        return [_sample_anomaly()]

    async def get_latest(self):
        anomaly = _sample_anomaly()
        return AnomalyRunResult(
            run_at="2026-07-19T00:00:00Z",
            detected=[AnomalyRunItem(anomaly=anomaly, reason="New anomaly detected.")],
        )

    async def get_by_id(self, anomaly_id):
        if anomaly_id == SAMPLE_ID:
            return _sample_anomaly()
        return None


@pytest.fixture
def override_dependencies():
    app.dependency_overrides[get_anomaly_engine] = lambda: MockAnomalyEngine()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_post_run_returns_200_with_results(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/anomalies/run?days=7")
        assert response.status_code == 200
        body = response.json()
        assert body["period"] == "Last 7 Days"
        assert len(body["detected"]) == 1


@pytest.mark.anyio
async def test_get_anomalies_returns_active_list(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/anomalies")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["status"] == "active"


@pytest.mark.anyio
async def test_get_latest_returns_run_result(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/anomalies/latest")
        assert response.status_code == 200
        body = response.json()
        assert len(body["detected"]) == 1


@pytest.mark.anyio
async def test_get_by_id_returns_anomaly(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/v1/anomalies/{SAMPLE_ID}")
        assert response.status_code == 200
        assert response.json()["id"] == str(SAMPLE_ID)


@pytest.mark.anyio
async def test_get_by_id_returns_404_when_missing(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/v1/anomalies/{uuid.uuid4()}")
        assert response.status_code == 404


@pytest.mark.anyio
async def test_latest_route_is_not_shadowed_by_id_route(override_dependencies):
    """Regression guard: '/anomalies/latest' must resolve to the latest-run
    endpoint, not be parsed as a UUID path parameter."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/anomalies/latest")
        assert response.status_code == 200
