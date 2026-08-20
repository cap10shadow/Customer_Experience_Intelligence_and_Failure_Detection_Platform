import uuid

import httpx
import pytest

from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.main import app

COMPLAINT_ID = str(uuid.uuid4())
DATASET_ID = str(uuid.uuid4())


def _complaint(**overrides):
    complaint = {
        "id": COMPLAINT_ID,
        "dataset_id": DATASET_ID,
        "inserted_at": "2026-08-08T00:00:00Z",
        "external_reference_id": "ext-1",
        "complaint_title": "Late delivery",
        "complaint_text": "My package arrived two weeks late and no one told me why.",
        "complaint_source": "web",
        "source_channel": "website_form",
        "normalized_title": None,
        "normalized_complaint_text": None,
        "customer_region": "us-east",
        "customer_segment": "individual",
        "customer_type": "existing_customer",
        "product_category": "shipping",
        "operational_area": "logistics",
        "service_type": None,
        "event_occurred_at": None,
        "complaint_status": "ingested",
        "processing_stage": "raw_ingestion",
        "is_deleted": False,
        "ingestion_source": None,
        "ingestion_batch_id": None,
        "source_record_hash": "abc123",
    }
    complaint.update(overrides)
    return complaint


def _client_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def override_http_client():
    def _apply(client: httpx.AsyncClient):
        app.dependency_overrides[get_http_client] = lambda: client

    yield _apply
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_get_complaint_by_id_returns_real_fields(override_http_client):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_complaint())

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/ingestion/complaints/{COMPLAINT_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == COMPLAINT_ID
    assert body["customerRegion"] == "us-east"
    assert body["operationalArea"] == "logistics"


@pytest.mark.anyio
async def test_get_complaint_not_found_returns_a_real_404(override_http_client):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/ingestion/complaints/{COMPLAINT_ID}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
