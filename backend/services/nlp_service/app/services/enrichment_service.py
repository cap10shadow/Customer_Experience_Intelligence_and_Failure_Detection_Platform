import time
import uuid
import logging
from typing import Optional

from backend.services.nlp_service.app.models.complaint_enrichment import ComplaintEnrichment
from backend.services.nlp_service.app.repositories.complaint_enrichment_repository import EnrichmentRepository
from backend.services.nlp_service.app.utils.classifiers import SentimentClassifier, UrgencyClassifier, IssueCategorizer
from backend.services.nlp_service.app.utils.text_processing import KeywordExtractor, Summarizer
from backend.services.nlp_service.app.schemas.complaint_enrichment import (
    ExplainabilityMetadata,
    HeuristicsNamespace,
    HeuristicExplanation
)

logger = logging.getLogger(__name__)

class EnrichmentService:
    """
    Deterministic Orchestration Service for NLP Enrichment.
    
    Philosophy:
    - Orchestrates lightweight, rule-based text processing.
    - Captures explainability metadata to ensure decisions are auditable.
    - Prevents duplicate processing via idempotency checks.
    """

    def __init__(self, repository: EnrichmentRepository):
        self.repository = repository

    async def enrich_complaint(
        self, complaint_id: uuid.UUID, text: str
    ) -> Optional[ComplaintEnrichment]:
        """
        Runs deterministic enrichment pipeline on a complaint.
        Returns the created ComplaintEnrichment entity.
        If already enriched, logs and returns None.
        """
        # Idempotency check
        if await self.repository.exists_for_complaint(complaint_id):
            logger.info(f"Complaint {complaint_id} is already enriched. Skipping.")
            return None

        start_time = time.perf_counter()

        # 1. Deterministic Classification
        sentiment_label, sentiment_kws = SentimentClassifier.classify(text)
        urgency_label, urgency_kws = UrgencyClassifier.classify(text)
        issue_category, issue_kws = IssueCategorizer.categorize(text)

        # 2. Text Processing
        extracted_keywords = KeywordExtractor.extract(text)
        summary = Summarizer.summarize(text)

        # 3. Explainability Metadata
        explainability = ExplainabilityMetadata(
            version="1.0",
            heuristics=HeuristicsNamespace(
                sentiment=HeuristicExplanation(
                    label=sentiment_label.value if sentiment_label else "unknown",
                    matched_keywords=sentiment_kws
                ),
                urgency=HeuristicExplanation(
                    label=urgency_label.value if urgency_label else "unknown",
                    matched_keywords=urgency_kws
                ),
                issue_category=HeuristicExplanation(
                    label=issue_category.value if issue_category else "unknown",
                    matched_keywords=issue_kws
                )
            )
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # 4. Construct Entity
        enrichment = ComplaintEnrichment(
            complaint_id=complaint_id,
            sentiment_label=sentiment_label,
            urgency_label=urgency_label,
            detected_issue_category=issue_category,
            extracted_keywords=extracted_keywords,
            complaint_summary=summary,
            model_name="deterministic_rules_engine",
            model_version="1.0.0",
            confidence_score=1.0,  # Deterministic rules have 100% confidence by definition
            processing_latency_ms=latency_ms,
            enrichment_source="rules_engine",
            explainability_metadata=explainability.model_dump()
        )

        # 5. Persist
        created_enrichment = await self.repository.create_enrichment(enrichment)
        logger.info(f"Successfully enriched complaint {complaint_id} in {latency_ms}ms.")

        return created_enrichment
