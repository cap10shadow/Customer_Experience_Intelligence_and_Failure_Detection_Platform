import uuid

import httpx
import pytest

from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.main import app

DATASET_ID = str(uuid.uuid4())
VERSION_ID = str(uuid.uuid4())
NEXT_VERSION_ID = str(uuid.uuid4())
INCIDENT_ID = str(uuid.uuid4())
COMPLAINT_ID = str(uuid.uuid4())


def _dataset(**overrides):
    dataset = {"id": DATASET_ID, "name": "Customer Complaints", "description": "Q1 data", "inserted_at": "2026-08-17T00:00:00Z"}
    dataset.update(overrides)
    return dataset


def _version(**overrides):
    version = {
        "id": VERSION_ID,
        "dataset_id": DATASET_ID,
        "version_number": 1,
        "status": "draft",
        "cumulative_record_count": 0,
        "new_record_count": 0,
        "analysis_started_at": None,
        "analysis_completed_at": None,
        "failure_reason": None,
        "inserted_at": "2026-08-17T00:00:00Z",
    }
    version.update(overrides)
    return version


def _complaint(**overrides):
    complaint = {
        "id": COMPLAINT_ID,
        "inserted_at": "2026-08-17T00:00:00Z",
        "dataset_id": DATASET_ID,
        "dataset_version_id": VERSION_ID,
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
async def test_create_dataset_forwards_to_ingestion_service(override_http_client):
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url).endswith("/datasets")
        return httpx.Response(201, json=_dataset())

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.post("/api/v1/datasets", json={"name": "Customer Complaints", "description": "Q1 data"})

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == DATASET_ID
    assert body["name"] == "Customer Complaints"


@pytest.mark.anyio
async def test_list_datasets_aggregates_versions_and_incident_count(override_http_client):
    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/datasets"):
            return httpx.Response(200, json=[_dataset()])
        if path.endswith("/versions"):
            return httpx.Response(200, json={"items": [_version(status="ready")]})
        if path.endswith("/incidents"):
            assert request.url.params["dataset_id"] == DATASET_ID
            return httpx.Response(200, json=[{"id": INCIDENT_ID}])
        raise AssertionError(f"Unexpected downstream call: {request.url}")

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/datasets")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == DATASET_ID
    assert body[0]["currentVersion"]["status"] == "ready"
    assert body[0]["openIncidentCount"] == 1


@pytest.mark.anyio
async def test_get_dataset_returns_latest_version_distinct_from_current_ready_version(override_http_client):
    """
    A brand-new dataset's only version is its v1 DRAFT -- `currentVersion`
    (ready-only) is None, but `latestVersion` must still surface it so the
    frontend never shows "No version yet" next to a Version History table
    that clearly has a v1 row.
    """

    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/versions"):
            return httpx.Response(200, json={"items": [_version(status="draft")]})
        return httpx.Response(200, json=_dataset())

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/datasets/{DATASET_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["currentVersion"] is None
    assert body["latestVersion"]["status"] == "draft"
    assert body["latestVersion"]["versionNumber"] == 1


@pytest.mark.anyio
async def test_dataset_responses_flag_the_legacy_dataset(override_http_client):
    import uuid as uuid_module

    from backend.shared.constants.seed_ids import LEGACY_DATASET_ID

    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/datasets"):
            return httpx.Response(200, json=[_dataset(id=str(LEGACY_DATASET_ID), name="Legacy / Demo Data")])
        if path.endswith("/versions"):
            return httpx.Response(200, json={"items": []})
        if path.endswith("/incidents"):
            return httpx.Response(200, json=[])
        raise AssertionError(f"Unexpected downstream call: {request.url}")

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/datasets")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["isLegacy"] is True
    assert uuid_module.UUID(body[0]["id"]) == LEGACY_DATASET_ID


@pytest.mark.anyio
async def test_get_dataset_not_found_returns_a_real_404(override_http_client):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/datasets/{DATASET_ID}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.anyio
async def test_archive_dataset_forwards_to_ingestion_service(override_http_client):
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        return httpx.Response(200, json=_dataset())

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.post(f"/api/v1/datasets/{DATASET_ID}/archive")

    assert response.status_code == 200
    assert captured["method"] == "POST"
    assert captured["path"].endswith(f"/datasets/{DATASET_ID}/archive")
    assert response.json()["id"] == DATASET_ID


@pytest.mark.anyio
async def test_archive_missing_dataset_returns_a_real_404(override_http_client):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.post(f"/api/v1/datasets/{DATASET_ID}/archive")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.anyio
async def test_post_dataset_complaint_requires_dataset_scope(override_http_client):
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(201, json=_complaint())

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.post(
            f"/api/v1/datasets/{DATASET_ID}/complaints",
            json={"complaint_text": "My package arrived two weeks late and no one told me why."},
        )

    assert response.status_code == 201
    assert f"dataset_id={DATASET_ID}" in captured["url"]
    body = response.json()
    assert body["id"] == COMPLAINT_ID


@pytest.mark.anyio
async def test_post_dataset_complaint_no_open_draft_returns_409(override_http_client):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"detail": "This dataset has no open draft version to ingest into."})

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.post(
            f"/api/v1/datasets/{DATASET_ID}/complaints",
            json={"complaint_text": "My package arrived two weeks late and no one told me why."},
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


@pytest.mark.anyio
async def test_finalize_and_analyze_happy_path_marks_version_ready(override_http_client):
    """
    End-to-end orchestration: finalize -> processing -> enrich -> analyzing
    -> anomaly run -> incident run -> list open incidents -> root cause ->
    business impact -> ready. One incident, no failures.
    """
    status_updates: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        method = request.method

        if path.endswith("/versions/finalize") and method == "POST":
            return httpx.Response(200, json=_version(status="ingesting", new_record_count=1, cumulative_record_count=1))

        if "/complaints" in path and method == "GET":
            return httpx.Response(200, json={"items": [_complaint()], "total_count": 1, "skip": 0, "limit": 500})

        if path.endswith("/enrichments/process") and method == "POST":
            return httpx.Response(200, json={"id": str(uuid.uuid4()), "complaint_id": COMPLAINT_ID})

        if path.endswith("/anomalies/run") and method == "POST":
            assert request.url.params["dataset_id"] == DATASET_ID
            assert request.url.params["dataset_version_id"] == VERSION_ID
            return httpx.Response(200, json={"detected": [], "updated": [], "resolved": []})

        if path.endswith("/incidents/run") and method == "POST":
            return httpx.Response(200, json={"created": [], "updated": [], "resolved": []})

        if path.endswith("/incidents") and method == "GET":
            return httpx.Response(200, json=[{"id": INCIDENT_ID, "status": "open"}])

        if path.endswith("/root-causes") and method == "POST":
            return httpx.Response(201, json={"id": str(uuid.uuid4())})

        if path.endswith("/business-impact") and method == "POST":
            return httpx.Response(201, json={"assessment_id": str(uuid.uuid4())})

        if path.endswith("/status") and method == "PATCH":
            import json as _json

            body = _json.loads(request.content)
            status_updates.append(body["status"])
            return httpx.Response(200, json=_version(status=body["status"], new_record_count=1, cumulative_record_count=1))

        raise AssertionError(f"Unexpected downstream call: {method} {request.url}")

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.post(f"/api/v1/datasets/{DATASET_ID}/versions/finalize")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert status_updates == ["processing", "analyzing", "ready"]


@pytest.mark.anyio
async def test_finalize_and_analyze_stage_failure_marks_version_failed_with_real_reason(override_http_client):
    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        method = request.method

        if path.endswith("/versions/finalize") and method == "POST":
            return httpx.Response(200, json=_version(status="ingesting", new_record_count=0, cumulative_record_count=0))

        if "/complaints" in path and method == "GET":
            return httpx.Response(200, json={"items": [], "total_count": 0, "skip": 0, "limit": 500})

        if path.endswith("/anomalies/run") and method == "POST":
            return httpx.Response(500)

        if path.endswith("/status") and method == "PATCH":
            import json as _json

            body = _json.loads(request.content)
            return httpx.Response(200, json=_version(status=body["status"], failure_reason=body.get("failure_reason")))

        raise AssertionError(f"Unexpected downstream call: {method} {request.url}")

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.post(f"/api/v1/datasets/{DATASET_ID}/versions/finalize")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["failureReason"] is not None
    assert "Anomaly detection failed" in body["failureReason"]


@pytest.mark.anyio
async def test_finalize_with_no_open_draft_returns_409(override_http_client):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"detail": "no draft"})

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.post(f"/api/v1/datasets/{DATASET_ID}/versions/finalize")

    assert response.status_code == 409
