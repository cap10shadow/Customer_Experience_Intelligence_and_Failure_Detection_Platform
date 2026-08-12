import pytest
from httpx import AsyncClient, ASGITransport
import uuid
from datetime import datetime

from backend.services.nlp_service.app.main import app
from backend.services.nlp_service.app.dependencies.services import get_enrichment_service, get_enrichment_repository
from backend.shared.constants.enums.complaint import SentimentLabel, UrgencyLabel, IssueCategory


class MockComplaintEnrichment:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# Mock repository
class MockEnrichmentRepository:
    def __init__(self):
        self.enrichments = {}

    async def get_by_complaint_id(self, complaint_id):
        for e in self.enrichments.values():
            if e.complaint_id == complaint_id:
                return e
        return None

    async def get_by_id(self, enrichment_id):
        return self.enrichments.get(enrichment_id)

    async def create_enrichment(self, enrichment):
        # assign an ID
        enrichment.id = uuid.uuid4()
        enrichment.inserted_at = datetime.utcnow()
        enrichment.enrichment_timestamp = datetime.utcnow()
        self.enrichments[enrichment.id] = enrichment
        return enrichment
        
    async def exists_for_complaint(self, complaint_id):
        return await self.get_by_complaint_id(complaint_id) is not None

    async def list_enrichments(self, skip=0, limit=100, **kwargs):
        items = list(self.enrichments.values())
        return items[skip:skip+limit]

    async def count_enrichments(self, **kwargs):
        return len(self.enrichments)

    async def summarize_by_category(self, issue_category, start_date, end_date):
        # Mock-only normalization: create_enrichment (below) stamps naive
        # datetime.utcnow(), while FastAPI parses these query params as
        # timezone-aware -- the real repository compares via SQLAlchemy/
        # Postgres, which has no such naive/aware mismatch.
        start_date = start_date.replace(tzinfo=None) if start_date.tzinfo else start_date
        end_date = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date
        matches = [
            enrichment
            for enrichment in self.enrichments.values()
            if getattr(enrichment, "detected_issue_category", None) == issue_category
            and start_date <= getattr(enrichment, "enrichment_timestamp") <= end_date
        ]
        sentiment_counts: dict = {}
        for enrichment in matches:
            label = getattr(enrichment, "sentiment_label", None)
            if label is None:
                continue
            key = label.value if hasattr(label, "value") else label
            sentiment_counts[key] = sentiment_counts.get(key, 0) + 1
        return len(matches), sentiment_counts


# Mock service
class MockEnrichmentService:
    def __init__(self, repository):
        self.repository = repository

    async def enrich_complaint(self, complaint_id, text):
        if await self.repository.exists_for_complaint(complaint_id):
            return None
        
        # Create a new enrichment
        enrichment = MockComplaintEnrichment(
            complaint_id=complaint_id,
            sentiment_label=SentimentLabel.NEGATIVE,
            urgency_label=UrgencyLabel.HIGH,
            detected_issue_category=IssueCategory.PRODUCT_ISSUE,
            extracted_keywords=["bad", "quality"],
            complaint_summary="Bad quality",
            model_name="mock_model",
            model_version="1.0",
            confidence_score=0.9,
            processing_latency_ms=10,
            enrichment_source="mock"
        )
        return await self.repository.create_enrichment(enrichment)


@pytest.fixture
def mock_repo():
    return MockEnrichmentRepository()


@pytest.fixture
def mock_service(mock_repo):
    return MockEnrichmentService(mock_repo)


@pytest.fixture
def override_dependencies(mock_repo, mock_service):
    app.dependency_overrides[get_enrichment_repository] = lambda: mock_repo
    app.dependency_overrides[get_enrichment_service] = lambda: mock_service
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.mark.anyio
async def test_process_enrichment_creates_new(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        complaint_id = str(uuid.uuid4())
        response = await client.post(
            "/api/v1/enrichments/process",
            json={
                "complaint_id": complaint_id,
                "text": "This product is terrible",
                "force_reprocess": False
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["complaint_id"] == complaint_id
        assert data["sentiment_label"] == "negative"


@pytest.mark.anyio
async def test_process_enrichment_idempotent(override_dependencies, mock_repo):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        complaint_id = str(uuid.uuid4())
        
        # First request should return 201
        response1 = await client.post(
            "/api/v1/enrichments/process",
            json={
                "complaint_id": complaint_id,
                "text": "This product is terrible"
            }
        )
        assert response1.status_code == 201
        data1 = response1.json()

        # Second request should return 200 and the same payload
        response2 = await client.post(
            "/api/v1/enrichments/process",
            json={
                "complaint_id": complaint_id,
                "text": "This product is terrible"
            }
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        assert data1["id"] == data2["id"]


@pytest.mark.anyio
async def test_list_enrichments_pagination(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/enrichments?limit=500")
        assert response.status_code == 200

        # Try to exceed limit
        response_invalid = await client.get("/api/v1/enrichments?limit=501")
        assert response_invalid.status_code == 422 # Validation error


# --- Step 7.X A-06: GET /enrichments/summary --------------------------------


@pytest.mark.anyio
async def test_enrichment_summary_returns_a_real_count_and_sentiment_breakdown(override_dependencies, mock_repo):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        for _ in range(2):
            await client.post(
                "/api/v1/enrichments/process",
                json={"complaint_id": str(uuid.uuid4()), "text": "This product is terrible"},
            )

        response = await client.get(
            "/api/v1/enrichments/summary",
            params={
                "issue_category": "product_issue",
                "start_date": "2020-01-01T00:00:00Z",
                "end_date": "2030-01-01T00:00:00Z",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["issue_category"] == "product_issue"
    assert body["total_count"] == 2
    assert body["sentiment_counts"] == {"negative": 2}


@pytest.mark.anyio
async def test_enrichment_summary_returns_an_honest_zero_result_not_a_404(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/v1/enrichments/summary",
            params={
                "issue_category": "delivery_issue",
                "start_date": "2020-01-01T00:00:00Z",
                "end_date": "2030-01-01T00:00:00Z",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 0
    assert body["sentiment_counts"] == {}


@pytest.mark.anyio
async def test_enrichment_summary_excludes_non_matching_categories(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post(
            "/api/v1/enrichments/process",
            json={"complaint_id": str(uuid.uuid4()), "text": "This product is terrible"},
        )

        # The mock enrichment service always classifies as PRODUCT_ISSUE --
        # querying a different category must not fabricate a match.
        response = await client.get(
            "/api/v1/enrichments/summary",
            params={
                "issue_category": "payment_issue",
                "start_date": "2020-01-01T00:00:00Z",
                "end_date": "2030-01-01T00:00:00Z",
            },
        )

    assert response.status_code == 200
    assert response.json()["total_count"] == 0


@pytest.mark.anyio
async def test_enrichment_summary_requires_all_three_query_parameters(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/enrichments/summary", params={"issue_category": "product_issue"})

    assert response.status_code == 422


@pytest.mark.anyio
async def test_enrichment_summary_rejects_an_unsupported_issue_category(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/v1/enrichments/summary",
            params={
                "issue_category": "not_a_real_category",
                "start_date": "2020-01-01T00:00:00Z",
                "end_date": "2030-01-01T00:00:00Z",
            },
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_enrichment_summary_route_is_registered_before_the_id_catchall(override_dependencies):
    """"/summary" must never be parsed as an {enrichment_id} UUID path param."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/v1/enrichments/summary",
            params={
                "issue_category": "product_issue",
                "start_date": "2020-01-01T00:00:00Z",
                "end_date": "2030-01-01T00:00:00Z",
            },
        )

    # A 422 here (rather than 200/404) would mean FastAPI tried to parse
    # "summary" as the {enrichment_id} UUID path -- registration order bug.
    assert response.status_code == 200
