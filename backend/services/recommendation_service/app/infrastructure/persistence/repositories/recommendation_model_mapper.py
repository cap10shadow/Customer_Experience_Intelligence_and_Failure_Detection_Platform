import uuid
from typing import Any, Dict

from backend.services.recommendation_service.app.domain.evidence_source import EvidenceSource
from backend.services.recommendation_service.app.domain.recommendation import Recommendation
from backend.services.recommendation_service.app.domain.recommendation_record import RecommendationRecord
from backend.services.recommendation_service.app.domain.supporting_evidence import SupportingEvidence
from backend.services.recommendation_service.app.infrastructure.persistence.models.recommendation_model import (
    RecommendationModel,
)


class RecommendationModelMapper:
    """
    Recommendation Model Mapper

    Operational Purpose:
    Translates between the Domain's `Recommendation`/`RecommendationRecord`
    and Infrastructure's `RecommendationModel` (ORM), including JSONB
    serialization/deserialization of `supporting_evidence`. The only place
    this boundary is crossed -- `PostgreSQLRecommendationRepository` never
    touches JSONB dict shapes directly, only this mapper.

    Pure translation only -- no business logic. Every field is copied
    verbatim; this mapper never validates, scores, or reinterprets
    anything.
    """

    @staticmethod
    def to_orm(recommendation: Recommendation, *, generation_id: uuid.UUID) -> RecommendationModel:
        return RecommendationModel(
            incident_id=recommendation.incident_id,
            generation_id=generation_id,
            category=recommendation.category,
            priority=recommendation.priority,
            score=recommendation.score,
            action=recommendation.action,
            recommendation_rationale=recommendation.rationale,
            priority_rationale=recommendation.priority_rationale,
            supporting_evidence=[
                RecommendationModelMapper._evidence_to_json(evidence) for evidence in recommendation.supporting_evidence
            ],
        )

    @staticmethod
    def to_domain(model: RecommendationModel) -> RecommendationRecord:
        recommendation = Recommendation(
            incident_id=model.incident_id,
            category=model.category,
            action=model.action,
            priority=model.priority,
            score=model.score,
            rationale=model.recommendation_rationale,
            priority_rationale=model.priority_rationale,
            supporting_evidence=tuple(
                RecommendationModelMapper._evidence_from_json(item) for item in model.supporting_evidence
            ),
        )
        return RecommendationRecord(
            recommendation_id=model.recommendation_id,
            recommendation=recommendation,
            generation_id=model.generation_id,
            created_at=model.created_at,
        )

    @staticmethod
    def _evidence_to_json(evidence: SupportingEvidence) -> Dict[str, Any]:
        return {"source": evidence.source.value, "description": evidence.description, "weight": evidence.weight}

    @staticmethod
    def _evidence_from_json(payload: Dict[str, Any]) -> SupportingEvidence:
        return SupportingEvidence(
            source=EvidenceSource(payload["source"]),
            description=payload["description"],
            weight=payload["weight"],
        )
