import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from backend.services.ingestion_service.app.dependencies.repositories import (
    get_complaint_repository,
    get_dataset_repository,
)
from backend.services.ingestion_service.app.main import app
from backend.shared.constants.enums.complaint import ComplaintStatus, SourceChannel
from backend.shared.constants.enums.dataset import DatasetVersionStatus
from backend.shared.constants.enums.enrichment import ProcessingStage

EXISTING_COMPLAINT_ID = uuid.uuid4()
MISSING_COMPLAINT_ID = uuid.uuid4()
DATASET_ID = uuid.uuid4()
DRAFT_VERSION_ID = uuid.uuid4()
MISSING_DATASET_ID = uuid.uuid4()
DUPLICATE_HASH = "duplicate-hash-value"


class _StubComplaint:
    """Plain object with the same attributes ComplaintResponse.model_validate reads."""

    def __init__(self, **overrides):
        self.id = EXISTING_COMPLAINT_ID
        self.inserted_at = datetime.now(timezone.utc)
        self.dataset_id = DATASET_ID
        self.dataset_version_id = DRAFT_VERSION_ID
        self.external_reference_id = "ext-1"
        self.complaint_title = "Late delivery"
        self.complaint_text = "My package arrived two weeks late and no one told me why."
        self.complaint_source = "web"
        self.source_channel = SourceChannel.WEBSITE_FORM
        self.normalized_title = None
        self.normalized_complaint_text = None
        self.customer_region = "us-east"
        self.customer_segment = None
        self.customer_type = None
        self.product_category = "shipping"
        self.operational_area = None
        self.service_type = None
        self.event_occurred_at = None
        self.complaint_status = ComplaintStatus.INGESTED
        self.processing_stage = ProcessingStage.RAW_INGESTION
        self.is_deleted = False
        self.ingestion_source = None
        self.ingestion_batch_id = None
        self.source_record_hash = "abc123"
        for key, value in overrides.items():
            setattr(self, key, value)


class _StubDataset:
    def __init__(self):
        self.id = DATASET_ID
        self.name = "Customer Complaints"
        self.description = None
        self.created_by = None
        self.is_deleted = False
        self.inserted_at = datetime.now(timezone.utc)


class _StubDraftVersion:
    def __init__(self, status=DatasetVersionStatus.DRAFT):
        self.id = DRAFT_VERSION_ID
        self.dataset_id = DATASET_ID
        self.version_number = 1
        self.status = status
        self.cumulative_record_count = 0
        self.new_record_count = 0
        self.analysis_started_at = None
        self.analysis_completed_at = None
        self.failure_reason = None
        self.inserted_at = datetime.now(timezone.utc)


class MockComplaintRepository:
    def __init__(self):
        self.created = []

    async def exists_by_source_record_hash(self, hash_val: str) -> bool:
        return hash_val == DUPLICATE_HASH

    async def create_complaint(self, complaint):
        self.created.append(complaint)
        return _StubComplaint(
            complaint_text=complaint.complaint_text,
            external_reference_id=complaint.external_reference_id,
            complaint_title=complaint.complaint_title,
            dataset_id=complaint.dataset_id,
            dataset_version_id=complaint.dataset_version_id,
        )

    async def get_by_id(self, complaint_id, include_deleted: bool = False):
        if complaint_id == EXISTING_COMPLAINT_ID:
            return _StubComplaint()
        return None

    async def list_complaints(self, **kwargs):
        return [_StubComplaint()]

    async def count_complaints(self, **kwargs):
        return 1


class MockDatasetRepository:
    def __init__(self, has_draft: bool = True):
        self.has_draft = has_draft

    async def get_dataset(self, dataset_id):
        if dataset_id == DATASET_ID:
            return _StubDataset()
        return None

    async def get_draft_version(self, dataset_id):
        if dataset_id == DATASET_ID and self.has_draft:
            return _StubDraftVersion()
        return None


@pytest.fixture
def mock_repos():
    complaint_repo = MockComplaintRepository()
    dataset_repo = MockDatasetRepository()
    app.dependency_overrides[get_complaint_repository] = lambda: complaint_repo
    app.dependency_overrides[get_dataset_repository] = lambda: dataset_repo
    yield complaint_repo, dataset_repo
    app.dependency_overrides.pop(get_complaint_repository, None)
    app.dependency_overrides.pop(get_dataset_repository, None)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_create_complaint_persists_and_returns_201(mock_repos):
    complaint_repo, _ = mock_repos
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            f"/complaints?dataset_id={DATASET_ID}",
            json={"complaint_text": "My package arrived two weeks late and no one told me why."},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["complaint_status"] == "ingested"
    assert body["processing_stage"] == "raw_ingestion"
    assert body["dataset_id"] == str(DATASET_ID)
    assert body["dataset_version_id"] == str(DRAFT_VERSION_ID)
    assert len(complaint_repo.created) == 1
    assert complaint_repo.created[0].dataset_id == DATASET_ID
    assert complaint_repo.created[0].dataset_version_id == DRAFT_VERSION_ID


@pytest.mark.anyio
async def test_create_complaint_requires_dataset_id_query_param(mock_repos):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/complaints", json={"complaint_text": "My package arrived two weeks late and no one told me why."}
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_complaint_missing_dataset_returns_404(mock_repos):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            f"/complaints?dataset_id={MISSING_DATASET_ID}",
            json={"complaint_text": "My package arrived two weeks late and no one told me why."},
        )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_create_complaint_no_open_draft_returns_409(mock_repos):
    _, dataset_repo = mock_repos
    dataset_repo.has_draft = False

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            f"/complaints?dataset_id={DATASET_ID}",
            json={"complaint_text": "My package arrived two weeks late and no one told me why."},
        )

    assert response.status_code == 409


@pytest.mark.anyio
async def test_create_complaint_rejects_text_shorter_than_minimum_length(mock_repos):
    complaint_repo, _ = mock_repos
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(f"/complaints?dataset_id={DATASET_ID}", json={"complaint_text": "too short"})

    assert response.status_code == 422
    assert len(complaint_repo.created) == 0


@pytest.mark.anyio
async def test_create_complaint_dedup_collision_returns_409(mock_repos, monkeypatch):
    complaint_repo, _ = mock_repos
    monkeypatch.setattr(
        "backend.services.ingestion_service.app.api.complaints.generate_complaint_hash",
        lambda *_args, **_kwargs: DUPLICATE_HASH,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            f"/complaints?dataset_id={DATASET_ID}",
            json={"complaint_text": "My package arrived two weeks late and no one told me why."},
        )

    assert response.status_code == 409
    assert len(complaint_repo.created) == 0


@pytest.mark.anyio
async def test_get_complaint_by_id_returns_200(mock_repos):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(f"/complaints/{EXISTING_COMPLAINT_ID}")

    assert response.status_code == 200
    assert response.json()["id"] == str(EXISTING_COMPLAINT_ID)


@pytest.mark.anyio
async def test_get_complaint_by_id_missing_returns_404(mock_repos):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(f"/complaints/{MISSING_COMPLAINT_ID}")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_list_complaints_returns_paginated_envelope(mock_repos):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/complaints?skip=0&limit=50")

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 1
    assert body["skip"] == 0
    assert body["limit"] == 50
    assert len(body["items"]) == 1


@pytest.mark.anyio
async def test_list_complaints_rejects_limit_above_maximum(mock_repos):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/complaints?limit=501")

    assert response.status_code == 422
