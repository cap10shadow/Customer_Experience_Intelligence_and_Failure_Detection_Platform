import uuid
from datetime import datetime
from typing import Optional, List, Any, Dict

from pydantic import BaseModel, ConfigDict, Field

from backend.shared.constants.enums.complaint import IssueCategory, SentimentLabel, UrgencyLabel


class HeuristicExplanation(BaseModel):
    """Specific explanation structure for a heuristic classification."""
    label: str
    matched_keywords: List[str] = Field(default_factory=list)
    method: str = "deterministic_keyword_matching"


class HeuristicsNamespace(BaseModel):
    """Namespace grouping for heuristic-based classifications."""
    sentiment: Optional[HeuristicExplanation] = None
    urgency: Optional[HeuristicExplanation] = None
    issue_category: Optional[HeuristicExplanation] = None


class ExplainabilityMetadata(BaseModel):
    """
    Extensible explainability metadata structure.
    Designed to support future namespaces (e.g., anomaly_detection, llm_reasoning).
    """
    version: str = Field(default="1.0", description="Schema version")
    heuristics: Optional[HeuristicsNamespace] = None

    model_config = ConfigDict(extra='allow')


class ComplaintEnrichmentBase(BaseModel):
    """Base schema for NLP enrichment data."""
    sentiment_label: Optional[SentimentLabel] = None
    urgency_label: Optional[UrgencyLabel] = None
    detected_issue_category: Optional[IssueCategory] = None
    extracted_keywords: Optional[List[str]] = None
    complaint_summary: Optional[str] = None

    model_name: str
    model_version: str
    confidence_score: Optional[float] = None
    processing_latency_ms: Optional[int] = None
    enrichment_source: str
    
    explainability_metadata: Optional[Dict[str, Any]] = None


class ComplaintEnrichmentCreate(ComplaintEnrichmentBase):
    """Schema for creating a new ComplaintEnrichment record."""
    complaint_id: uuid.UUID


class ProcessEnrichmentRequest(BaseModel):
    """Schema for processing a new enrichment request."""
    complaint_id: uuid.UUID
    text: str = Field(..., min_length=1)
    force_reprocess: bool = False


class ComplaintEnrichmentResponse(ComplaintEnrichmentBase):
    """Schema representing a full ComplaintEnrichment record."""
    id: uuid.UUID
    complaint_id: uuid.UUID
    enrichment_timestamp: datetime
    inserted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplaintEnrichmentListResponse(BaseModel):
    """Paginated list response for ComplaintEnrichments."""
    items: List[ComplaintEnrichmentResponse]
    total: int
    page: int
    size: int
