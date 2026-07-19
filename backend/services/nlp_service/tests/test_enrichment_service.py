import uuid

import pytest

from backend.services.nlp_service.app.services.enrichment_service import EnrichmentService
from backend.services.nlp_service.app.models.complaint_enrichment import ComplaintEnrichment
from backend.shared.constants.enums.complaint import IssueCategory, SentimentLabel, UrgencyLabel


class FakeEnrichmentRepository:
    """In-memory stand-in for EnrichmentRepository, used to exercise the
    real orchestration logic in EnrichmentService without a database."""

    def __init__(self):
        self._by_complaint_id = {}

    async def exists_for_complaint(self, complaint_id):
        return complaint_id in self._by_complaint_id

    async def create_enrichment(self, enrichment: ComplaintEnrichment):
        self._by_complaint_id[enrichment.complaint_id] = enrichment
        return enrichment


@pytest.fixture
def repository():
    return FakeEnrichmentRepository()


@pytest.fixture
def service(repository):
    return EnrichmentService(repository)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_enrich_complaint_combines_all_component_outputs(service):
    complaint_id = uuid.uuid4()
    text = "This is unacceptable, the payment was double charged and I am furious, escalate this now."

    enrichment = await service.enrich_complaint(complaint_id=complaint_id, text=text)

    assert enrichment.complaint_id == complaint_id
    assert enrichment.sentiment_label == SentimentLabel.HIGHLY_NEGATIVE
    assert enrichment.urgency_label == UrgencyLabel.HIGH
    assert enrichment.detected_issue_category == IssueCategory.PAYMENT_ISSUE
    assert "charged" in enrichment.extracted_keywords
    assert enrichment.complaint_summary.startswith("This is unacceptable")
    assert enrichment.model_name == "deterministic_rules_engine"
    assert enrichment.confidence_score == 1.0
    assert enrichment.enrichment_source == "rules_engine"

    heuristics = enrichment.explainability_metadata["heuristics"]
    assert heuristics["sentiment"]["label"] == "highly_negative"
    assert heuristics["urgency"]["label"] == "high"
    assert heuristics["issue_category"]["label"] == "payment_issue"


@pytest.mark.anyio
async def test_enrich_complaint_is_idempotent(service, repository):
    complaint_id = uuid.uuid4()
    await service.enrich_complaint(complaint_id=complaint_id, text="Great support, thanks!")

    result = await service.enrich_complaint(complaint_id=complaint_id, text="Great support, thanks!")

    assert result is None
