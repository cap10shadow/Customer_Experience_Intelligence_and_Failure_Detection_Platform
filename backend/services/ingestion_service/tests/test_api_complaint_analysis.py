import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from backend.services.ingestion_service.app.dependencies.repositories import (
    get_complaint_repository,
    get_dataset_repository,
    get_field_alias_suggestion_repository,
    get_field_value_mapping_repository,
)
from backend.services.ingestion_service.app.main import app
from backend.services.ingestion_service.app.models.field_alias_suggestion import FieldAliasSuggestion
from backend.services.ingestion_service.tests._fakes import (
    FakeFieldAliasSuggestionRepository,
    FakeFieldValueMappingRepository,
)
from backend.shared.constants.enums.dataset import DatasetVersionStatus
from backend.shared.constants.enums.field_mapping import FieldValueMappingConfidence, FieldValueMappingType

DATASET_ID = uuid.uuid4()
DRAFT_VERSION_ID = uuid.uuid4()
MISSING_DATASET_ID = uuid.uuid4()


class _StubDataset:
    def __init__(self):
        self.id = DATASET_ID
        self.name = "Analysis Test Dataset"
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


class MockComplaintRepository:
    def __init__(self):
        self.created = []
        self.existing_hashes: set[str] = set()

    async def bulk_exists_by_source_record_hash(self, hashes):
        return {h for h in hashes if h in self.existing_hashes}

    async def create_complaints_bulk(self, complaints):
        self.created.extend(complaints)
        for c in complaints:
            self.existing_hashes.add(c.source_record_hash)
        return {c.id for c in complaints}


@pytest.fixture
def mock_repos():
    complaint_repo = MockComplaintRepository()
    dataset_repo = MockDatasetRepository()
    mapping_repo = FakeFieldValueMappingRepository()
    alias_repo = FakeFieldAliasSuggestionRepository()
    app.dependency_overrides[get_complaint_repository] = lambda: complaint_repo
    app.dependency_overrides[get_dataset_repository] = lambda: dataset_repo
    app.dependency_overrides[get_field_value_mapping_repository] = lambda: mapping_repo
    app.dependency_overrides[get_field_alias_suggestion_repository] = lambda: alias_repo
    yield complaint_repo, dataset_repo, mapping_repo, alias_repo
    app.dependency_overrides.pop(get_complaint_repository, None)
    app.dependency_overrides.pop(get_dataset_repository, None)
    app.dependency_overrides.pop(get_field_value_mapping_repository, None)
    app.dependency_overrides.pop(get_field_alias_suggestion_repository, None)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _row(row_number, complaint_text="A sufficiently long complaint text for testing.", **overrides):
    row = {"row_number": row_number, "complaint_text": complaint_text}
    row.update(overrides)
    return row


@pytest.mark.anyio
async def test_analyze_requires_analysis_session_id(mock_repos):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            f"/complaints:analyze?dataset_id={DATASET_ID}", json={"rows": [_row(1)]}
        )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_analyze_missing_dataset_returns_404(mock_repos):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            f"/complaints:analyze?dataset_id={MISSING_DATASET_ID}",
            json={"analysis_session_id": str(uuid.uuid4()), "rows": [_row(1)]},
        )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_analyze_classifies_high_medium_low_and_rejected(mock_repos):
    _, _, mapping_repo, alias_repo = mock_repos
    await alias_repo.create(
        FieldAliasSuggestion(
            field_name="operational_area",
            source_value_normalized="courier partner",
            suggested_target_value="logistics",
        )
    )

    rows = [
        _row(1, operational_area="logistics"),  # HIGH -- exact enum match
        _row(2, operational_area="Courier Partner"),  # MEDIUM -- registry match
        _row(3, operational_area="ABC Operations"),  # LOW -- no match
        _row(4, complaint_text="short"),  # rejected -- structurally invalid
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            f"/complaints:analyze?dataset_id={DATASET_ID}",
            json={"analysis_session_id": str(uuid.uuid4()), "rows": rows},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == {"accepted": 1, "auto_normalized": 0, "suggested_mapping": 1, "needs_review": 1, "rejected": 1}
    assert body["total_rows"] == 4
    assert len(body["pending_clusters"]) == 2
    # no Complaint rows persisted by :analyze
    assert mock_repos[0].created == []


@pytest.mark.anyio
async def test_analyze_paginates_results(mock_repos):
    rows = [_row(i, operational_area="logistics") for i in range(1, 61)]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            f"/complaints:analyze?dataset_id={DATASET_ID}&page=1&page_size=25",
            json={"analysis_session_id": str(uuid.uuid4()), "rows": rows},
        )
    body = response.json()
    assert len(body["results"]) == 25
    assert body["total_rows"] == 60
    assert body["total_pages"] == 3


@pytest.mark.anyio
async def test_reanalyzing_same_session_does_not_inflate_occurrence_count(mock_repos):
    _, _, mapping_repo, alias_repo = mock_repos
    rows = [_row(1, operational_area="ABC Operations")]
    session_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        r1 = await client.post(
            f"/complaints:analyze?dataset_id={DATASET_ID}", json={"analysis_session_id": session_id, "rows": rows}
        )
        r2 = await client.post(
            f"/complaints:analyze?dataset_id={DATASET_ID}", json={"analysis_session_id": session_id, "rows": rows}
        )
    c1 = r1.json()["pending_clusters"][0]["occurrence_count"]
    c2 = r2.json()["pending_clusters"][0]["occurrence_count"]
    assert c1 == 1
    assert c2 == 1


@pytest.mark.anyio
async def test_analyze_routes_unfamiliar_strict_enum_values_to_mapping_not_hard_rejection(mock_repos):
    """D05: customer_type/service_type/source_channel/customer_segment must enter Mapping
    Review instead of failing as a structural invalid_enum rejection."""
    rows = [
        _row(1, customer_type="small_business"),  # unfamiliar -- LOW, needs_review
        _row(2, service_type="returns_handling"),  # unfamiliar -- LOW, needs_review
        _row(3, source_channel="phone"),  # unfamiliar -- LOW, needs_review
        _row(4, customer_segment="enterprise_account"),  # unfamiliar -- LOW, needs_review
        _row(5, customer_type="existing_customer"),  # HIGH -- exact enum match
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            f"/complaints:analyze?dataset_id={DATASET_ID}",
            json={"analysis_session_id": str(uuid.uuid4()), "rows": rows},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["rejected"] == 0
    assert body["summary"]["needs_review"] == 4
    assert body["summary"]["accepted"] == 1
    assert len(body["pending_clusters"]) == 4
    fields_needing_mapping = {c["field_name"] for c in body["pending_clusters"]}
    assert fields_needing_mapping == {"customer_type", "service_type", "source_channel", "customer_segment"}


@pytest.mark.anyio
async def test_analyze_exposes_valid_choices_for_enum_backed_fields(mock_repos):
    """D04/D08: enum-backed mapped fields must return their valid canonical choices;
    free-text customer_region must not."""
    rows = [
        _row(1, operational_area="Not A Real Area"),
        _row(2, customer_region="Kochi"),
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            f"/complaints:analyze?dataset_id={DATASET_ID}",
            json={"analysis_session_id": str(uuid.uuid4()), "rows": rows},
        )
    body = response.json()
    clusters = {c["field_name"]: c for c in body["pending_clusters"]}
    assert clusters["operational_area"]["valid_choices"] is not None
    assert "customer_support" in clusters["operational_area"]["valid_choices"]
    assert clusters["customer_region"]["valid_choices"] is None


@pytest.mark.anyio
async def test_analyze_echoes_source_file_name_per_row(mock_repos):
    """D01/D17: the upload manifest's per-file row counts depend on source_file_name
    surviving the :analyze round trip unchanged."""
    rows = [
        _row(1, source_file_name="Upload_Ready_240.csv"),
        _row(2, source_file_name="Mixed_Batch_100.csv"),
        _row(3),  # no file -- manually-added row
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            f"/complaints:analyze?dataset_id={DATASET_ID}",
            json={"analysis_session_id": str(uuid.uuid4()), "rows": rows},
        )
    body = response.json()
    by_row = {r["row_number"]: r["source_file_name"] for r in body["results"]}
    assert by_row[1] == "Upload_Ready_240.csv"
    assert by_row[2] == "Mixed_Batch_100.csv"
    assert by_row[3] is None


@pytest.mark.anyio
async def test_batch_echoes_source_file_name_per_outcome(mock_repos):
    """Same contract on :batch -- lets the client attribute created/duplicate/rejected
    outcomes back to the file they came from."""
    rows = [
        _row(1, operational_area="logistics", source_file_name="fileA.csv"),
        _row(2, complaint_text="short", source_file_name="fileB.csv"),  # rejected
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            f"/complaints:batch?dataset_id={DATASET_ID}",
            json={"analysis_session_id": str(uuid.uuid4()), "rows": rows},
        )
    body = response.json()
    by_row = {o["row_number"]: o["source_file_name"] for o in body["outcomes"]}
    assert by_row[1] == "fileA.csv"
    assert by_row[2] == "fileB.csv"


@pytest.mark.anyio
async def test_batch_reclassifies_rows_that_lose_a_concurrent_insert_race(mock_repos):
    """WP-E: if create_complaints_bulk reports fewer persisted ids than rows queued as
    'created' (the DB unique constraint caught a same-hash row inserted concurrently,
    after this request's own bulk_exists_by_source_record_hash check already passed),
    the response must reclassify that row as 'duplicate', never silently claim it was
    created when the database rejected it."""
    complaint_repo, _, _, _ = mock_repos

    original_bulk = complaint_repo.create_complaints_bulk

    async def racing_bulk(complaints):
        persisted = await original_bulk(complaints)
        # Simulate row 2 losing a concurrent race: excluded from what actually persisted.
        losers = {c.id for c in complaints if c.complaint_text.endswith("row two.")}
        return persisted - losers

    complaint_repo.create_complaints_bulk = racing_bulk

    rows = [
        _row(1, operational_area="logistics", complaint_text="A sufficiently long complaint text, row one."),
        _row(2, operational_area="logistics", complaint_text="A sufficiently long complaint text, row two."),
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            f"/complaints:batch?dataset_id={DATASET_ID}",
            json={"analysis_session_id": str(uuid.uuid4()), "rows": rows},
        )
    body = response.json()
    outcomes_by_row = {o["row_number"]: o for o in body["outcomes"]}
    assert outcomes_by_row[1]["outcome"] == "created"
    assert outcomes_by_row[2]["outcome"] == "duplicate"
    assert "concurrent" in outcomes_by_row[2]["reason"]
    assert body["created_count"] == 1
    assert body["duplicate_count"] == 1
    assert len(body["outcomes"]) == len(rows)


@pytest.mark.anyio
async def test_batch_requires_open_draft(mock_repos):
    _, dataset_repo, _, _ = mock_repos
    dataset_repo.has_draft = False
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            f"/complaints:batch?dataset_id={DATASET_ID}",
            json={"analysis_session_id": str(uuid.uuid4()), "rows": [_row(1, operational_area="logistics")]},
        )
    assert response.status_code == 409


@pytest.mark.anyio
async def test_batch_accounts_for_every_row_zero_loss(mock_repos):
    rows = [
        _row(1, operational_area="logistics"),  # created
        _row(2, operational_area="ABC Operations"),  # rejected -- needs_mapping unresolved
        _row(3, complaint_text="short"),  # rejected -- structurally invalid
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            f"/complaints:batch?dataset_id={DATASET_ID}",
            json={"analysis_session_id": str(uuid.uuid4()), "rows": rows},
        )
    assert response.status_code == 200
    body = response.json()
    assert len(body["outcomes"]) == 3
    assert body["created_count"] == 1
    assert body["rejected_count"] == 2
    assert body["created_count"] + body["duplicate_count"] + body["rejected_count"] == body["total_rows"]


@pytest.mark.anyio
async def test_batch_detects_duplicates_within_and_across_calls(mock_repos):
    rows = [
        _row(1, external_reference_id="ext-1", operational_area="logistics"),
        _row(2, external_reference_id="ext-1", operational_area="logistics"),  # intra-batch duplicate
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            f"/complaints:batch?dataset_id={DATASET_ID}",
            json={"analysis_session_id": str(uuid.uuid4()), "rows": rows},
        )
        assert response.json()["created_count"] == 1
        assert response.json()["duplicate_count"] == 1

        # same row again, new call -- now an across-calls duplicate
        response2 = await client.post(
            f"/complaints:batch?dataset_id={DATASET_ID}",
            json={"analysis_session_id": str(uuid.uuid4()), "rows": [rows[0]]},
        )
    assert response2.json()["duplicate_count"] == 1
    assert response2.json()["created_count"] == 0


@pytest.mark.anyio
async def test_batch_preserves_raw_and_canonical_values(mock_repos):
    complaint_repo, _, mapping_repo, _ = mock_repos
    mapping = await mapping_repo.create(
        field_name="customer_region",
        raw_value_normalized="home delivery",
        raw_value_original_example="Home Delivery",
        confidence=FieldValueMappingConfidence.MEDIUM,
        suggested_target_value="delivery",
    )
    await mapping_repo.set_approved(
        mapping.id,
        target_value="delivery",
        mapping_type=FieldValueMappingType.ALIAS,
        reviewed_by="tester",
    )

    rows = [_row(1, customer_region="Home Delivery")]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            f"/complaints:batch?dataset_id={DATASET_ID}",
            json={"analysis_session_id": str(uuid.uuid4()), "rows": rows},
        )
    assert response.status_code == 200
    assert len(complaint_repo.created) == 1
    created = complaint_repo.created[0]
    assert created.customer_region == "delivery"
    assert created.raw_customer_region == "Home Delivery"
