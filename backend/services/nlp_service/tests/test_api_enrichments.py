import pytest
from httpx import AsyncClient, ASGITransport
import uuid
from datetime import datetime

from backend.services.nlp_service.app.main import app
from backend.services.nlp_service.app.dependencies.services import get_enrichment_service, get_enrichment_repository
from backend.services.ingestion_service.app.models.complaint import Complaint
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
