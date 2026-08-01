import uuid
from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel

from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.recommendation_record import RecommendationRecord


class SupportingEvidenceResponse(BaseModel):
    source: str
    description: str
    weight: int


class RecommendationSummaryResponse(BaseModel):
    """
    Lightweight Recommendation DTO for collection endpoints (ARB-approved
    refinement). Deliberately excludes `supporting_evidence`,
    `recommendation_rationale`, and `priority_rationale` to avoid payload
    bloat when listing many Recommendations at once -- those are available
    via `GET /recommendations/{recommendation_id}` (`RecommendationDetailResponse`).
    """

    recommendation_id: uuid.UUID
    incident_id: str
    generation_id: uuid.UUID
    category: RecommendationCategory
    priority: RecommendationPriority
    score: int
    action: str
    created_at: datetime

    @staticmethod
    def from_record(record: RecommendationRecord) -> "RecommendationSummaryResponse":
        recommendation = record.recommendation
        return RecommendationSummaryResponse(
            recommendation_id=record.recommendation_id,
            incident_id=recommendation.incident_id,
            generation_id=record.generation_id,
            category=recommendation.category,
            priority=recommendation.priority,
            score=recommendation.score,
            action=recommendation.action,
            created_at=record.created_at,
        )


class RecommendationDetailResponse(BaseModel):
    """
    Full, explainable Recommendation DTO -- returned only by
    `GET /recommendations/{recommendation_id}` (ARB-approved refinement).
    Contains every field a `RecommendationSummaryResponse` omits.
    """

    recommendation_id: uuid.UUID
    incident_id: str
    generation_id: uuid.UUID
    category: RecommendationCategory
    priority: RecommendationPriority
    score: int
    action: str
    recommendation_rationale: str
    priority_rationale: str
    supporting_evidence: List[SupportingEvidenceResponse]
    created_at: datetime

    @staticmethod
    def from_record(record: RecommendationRecord) -> "RecommendationDetailResponse":
        recommendation = record.recommendation
        return RecommendationDetailResponse(
            recommendation_id=record.recommendation_id,
            incident_id=recommendation.incident_id,
            generation_id=record.generation_id,
            category=recommendation.category,
            priority=recommendation.priority,
            score=recommendation.score,
            action=recommendation.action,
            recommendation_rationale=recommendation.rationale,
            priority_rationale=recommendation.priority_rationale,
            supporting_evidence=[
                SupportingEvidenceResponse(source=evidence.source.value, description=evidence.description, weight=evidence.weight)
                for evidence in recommendation.supporting_evidence
            ],
            created_at=record.created_at,
        )


class RecommendationStatisticsResponse(BaseModel):
    """Aggregate statistics computed across all persisted Recommendations (see RecommendationStatisticsService)."""

    total_count: int
    category_counts: Dict[str, int]
    priority_counts: Dict[str, int]
    average_score: float
