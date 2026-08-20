import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from backend.services.ingestion_service.app.dependencies.repositories import get_dataset_repository
from backend.services.ingestion_service.app.main import app
from backend.shared.constants.enums.dataset import DatasetVersionStatus

DATASET_ID = uuid.uuid4()
VERSION_ID = uuid.uuid4()
MISSING_DATASET_ID = uuid.uuid4()


class _StubDataset:
    def __init__(self, dataset_id=DATASET_ID, name="Customer Complaints"):
        self.id = dataset_id
        self.name = name
        self.description = None
        self.created_by = None
        self.is_deleted = False
        self.inserted_at = datetime.now(timezone.utc)


class _StubVersion:
    def __init__(self, version_id=VERSION_ID, dataset_id=DATASET_ID, version_number=1, status=DatasetVersionStatus.DRAFT, **overrides):
        self.id = version_id
        self.dataset_id = dataset_id
        self.version_number = version_number
        self.status = status
        self.cumulative_record_count = 0
        self.new_record_count = 0
        self.analysis_started_at = None
        self.analysis_completed_at = None
        self.failure_reason = None
        self.inserted_at = datetime.now(timezone.utc)
        for key, value in overrides.items():
            setattr(self, key, value)


class MockDatasetRepository:
    def __init__(self):
        self.datasets = {}
        self.versions = {}
        self.saved_versions = []

    async def create_dataset(self, dataset):
        # Mimics what a real flush/INSERT would populate (server_default /
        # Python-level `default=`) -- the plain constructed object doesn't
        # have these set yet, exactly like the real SQLAlchemy model.
        dataset.id = dataset.id or DATASET_ID
        dataset.is_deleted = False
        dataset.inserted_at = datetime.now(timezone.utc)
        self.datasets[dataset.id] = dataset
        return dataset

    async def get_dataset(self, dataset_id, include_deleted=False):
        dataset = self.datasets.get(dataset_id)
        if dataset is not None and dataset.is_deleted and not include_deleted:
            return None
        return dataset

    async def list_datasets(self, include_deleted=False):
        if include_deleted:
            return list(self.datasets.values())
        return [d for d in self.datasets.values() if not d.is_deleted]

    async def archive_dataset(self, dataset_id):
        dataset = self.datasets.get(dataset_id)
        if dataset is None:
            return None
        dataset.is_deleted = True
        return dataset

    async def create_dataset_version(self, version):
        self.versions[version.id] = version
        return version

    async def get_dataset_version(self, version_id):
        return self.versions.get(version_id)

    async def list_dataset_versions(self, dataset_id):
        return [v for v in self.versions.values() if v.dataset_id == dataset_id]

    async def get_draft_version(self, dataset_id):
        for v in self.versions.values():
            if v.dataset_id == dataset_id and v.status == DatasetVersionStatus.DRAFT:
                return v
        return None

    async def save_version(self, version):
        self.saved_versions.append(version)
        return version

    async def count_complaints_in_dataset(self, dataset_id):
        return 42

    async def count_complaints_in_version(self, dataset_version_id):
        return 7


@pytest.fixture
def mock_repo():
    repo = MockDatasetRepository()
    app.dependency_overrides[get_dataset_repository] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_dataset_repository, None)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_create_dataset_also_opens_version_1_draft(mock_repo):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/datasets", json={"name": "Customer Complaints", "description": "Q1 data"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Customer Complaints"

    dataset_id = uuid.UUID(body["id"])
    versions = [v for v in mock_repo.versions.values() if v.dataset_id == dataset_id]
    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert versions[0].status == DatasetVersionStatus.DRAFT


@pytest.mark.anyio
async def test_get_dataset_not_found_returns_404(mock_repo):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(f"/datasets/{MISSING_DATASET_ID}")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_list_datasets_returns_created_datasets(mock_repo):
    mock_repo.datasets[DATASET_ID] = _StubDataset()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/datasets")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(DATASET_ID)


@pytest.mark.anyio
async def test_archive_dataset_sets_is_deleted(mock_repo):
    mock_repo.datasets[DATASET_ID] = _StubDataset()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(f"/datasets/{DATASET_ID}/archive")

    assert response.status_code == 200
    assert mock_repo.datasets[DATASET_ID].is_deleted is True


@pytest.mark.anyio
async def test_archive_missing_dataset_returns_404(mock_repo):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(f"/datasets/{MISSING_DATASET_ID}/archive")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_archived_dataset_disappears_from_get_and_list_but_versions_stay_addressable(mock_repo):
    """WP-D: archiving hides the dataset from default lookups without touching its versions."""
    mock_repo.datasets[DATASET_ID] = _StubDataset()
    mock_repo.versions[VERSION_ID] = _StubVersion(status=DatasetVersionStatus.READY)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        archive_response = await client.post(f"/datasets/{DATASET_ID}/archive")
        assert archive_response.status_code == 200

        get_response = await client.get(f"/datasets/{DATASET_ID}")
        assert get_response.status_code == 404

        list_response = await client.get("/datasets")
        assert list_response.status_code == 200
        assert all(d["id"] != str(DATASET_ID) for d in list_response.json())

        # Provenance/history: the version row itself is untouched and still
        # directly addressable -- archiving a Dataset never cascades to its
        # DatasetVersions (only a real ON DELETE CASCADE on hard-delete would,
        # and this is a soft-delete flag flip, not a delete).
        version_response = await client.get(f"/datasets/{DATASET_ID}/versions/{VERSION_ID}")
        assert version_response.status_code == 200
        assert version_response.json()["status"] == "ready"


@pytest.mark.anyio
async def test_finalize_version_snapshots_counts_and_opens_next_draft(mock_repo):
    mock_repo.datasets[DATASET_ID] = _StubDataset()
    mock_repo.versions[VERSION_ID] = _StubVersion(status=DatasetVersionStatus.DRAFT)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(f"/datasets/{DATASET_ID}/versions/finalize")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ingesting"
    assert body["new_record_count"] == 7
    assert body["cumulative_record_count"] == 42

    # A new draft (version 2) must now be open for future ingestion.
    remaining_drafts = [
        v for v in mock_repo.versions.values() if v.dataset_id == DATASET_ID and v.status == DatasetVersionStatus.DRAFT
    ]
    assert len(remaining_drafts) == 1
    assert remaining_drafts[0].version_number == 2


@pytest.mark.anyio
async def test_finalize_version_with_no_open_draft_returns_409(mock_repo):
    mock_repo.datasets[DATASET_ID] = _StubDataset()
    # No DRAFT version registered -- e.g. already finalized.

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(f"/datasets/{DATASET_ID}/versions/finalize")

    assert response.status_code == 409


@pytest.mark.anyio
async def test_update_version_status_to_ready_stamps_completed_at(mock_repo):
    mock_repo.datasets[DATASET_ID] = _StubDataset()
    mock_repo.versions[VERSION_ID] = _StubVersion(status=DatasetVersionStatus.ANALYZING)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.patch(f"/datasets/{DATASET_ID}/versions/{VERSION_ID}/status", json={"status": "ready"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["analysis_completed_at"] is not None


@pytest.mark.anyio
async def test_update_version_status_to_failed_records_failure_reason(mock_repo):
    mock_repo.datasets[DATASET_ID] = _StubDataset()
    mock_repo.versions[VERSION_ID] = _StubVersion(status=DatasetVersionStatus.ANALYZING)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.patch(
            f"/datasets/{DATASET_ID}/versions/{VERSION_ID}/status",
            json={"status": "failed", "failure_reason": "anomaly_service returned a 500"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["failure_reason"] == "anomaly_service returned a 500"
