import uuid
from typing import List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.recommendation_service.app.domain.recommendation import Recommendation
from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.recommendation_record import RecommendationRecord
from backend.services.recommendation_service.app.domain.recommendation_repository import RecommendationRepository
from backend.services.recommendation_service.app.infrastructure.persistence.models.recommendation_generation_model import (
    RecommendationGenerationModel,
)
from backend.services.recommendation_service.app.infrastructure.persistence.models.recommendation_model import (
    RecommendationModel,
)
from backend.services.recommendation_service.app.infrastructure.persistence.repositories.recommendation_model_mapper import (
    RecommendationModelMapper,
)


class PostgreSQLRecommendationRepository(RecommendationRepository):
    """
    PostgreSQL Recommendation Repository

    Ownership:
    Owned by the Recommendation Service's infrastructure layer.

    Operational Purpose:
    Concrete, PostgreSQL/SQLAlchemy implementation of the Domain-defined
    `RecommendationRepository` port. Responsible strictly for database
    persistence and retrieval -- no business logic, no scoring, no rule or
    engine execution.

    Architectural Boundaries:
    - Recommendations are immutable and append-only: this class exposes no
      update or delete operation, and never issues an UPDATE/DELETE
      against `recommendations` or `recommendation_generations`.
    - `save_many()` persists exactly one `RecommendationGeneration` row
      (using the `generation_id` its caller supplies -- this repository
      never generates one) plus one `RecommendationModel` row per
      `Recommendation`, including when `recommendations` is empty: the
      generation row is still written, preserving the audit trail that an
      engine execution happened for this incident even when it produced
      zero Recommendations.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_many(
        self,
        recommendations: Sequence[Recommendation],
        *,
        incident_id: str,
        generation_id: uuid.UUID,
    ) -> List[RecommendationRecord]:
        generation_model = RecommendationGenerationModel(generation_id=generation_id, incident_id=incident_id)
        self.session.add(generation_model)

        models = [
            RecommendationModelMapper.to_orm(recommendation, generation_id=generation_id)
            for recommendation in recommendations
        ]
        self.session.add_all(models)
        await self.session.flush()

        return [RecommendationModelMapper.to_domain(model) for model in models]

    async def get_by_id(self, recommendation_id: uuid.UUID) -> Optional[RecommendationRecord]:
        stmt = select(RecommendationModel).where(RecommendationModel.recommendation_id == recommendation_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return RecommendationModelMapper.to_domain(model) if model is not None else None

    async def list_by_incident(
        self, incident_id: Optional[str] = None, *, limit: int, offset: int
    ) -> List[RecommendationRecord]:
        stmt = select(RecommendationModel)
        if incident_id is not None:
            stmt = stmt.where(RecommendationModel.incident_id == incident_id)
        stmt = stmt.order_by(RecommendationModel.created_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        return [RecommendationModelMapper.to_domain(model) for model in result.scalars().all()]

    async def list_by_generation(
        self, generation_id: uuid.UUID, *, limit: int, offset: int
    ) -> List[RecommendationRecord]:
        stmt = (
            select(RecommendationModel)
            .where(RecommendationModel.generation_id == generation_id)
            .order_by(RecommendationModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return [RecommendationModelMapper.to_domain(model) for model in result.scalars().all()]

    async def list_by_category(
        self, category: RecommendationCategory, *, limit: int, offset: int
    ) -> List[RecommendationRecord]:
        stmt = (
            select(RecommendationModel)
            .where(RecommendationModel.category == category)
            .order_by(RecommendationModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return [RecommendationModelMapper.to_domain(model) for model in result.scalars().all()]

    async def list_by_priority(
        self, priority: RecommendationPriority, *, limit: int, offset: int
    ) -> List[RecommendationRecord]:
        stmt = (
            select(RecommendationModel)
            .where(RecommendationModel.priority == priority)
            .order_by(RecommendationModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return [RecommendationModelMapper.to_domain(model) for model in result.scalars().all()]

    async def get_latest_by_incident(
        self, incident_id: str, *, limit: int, offset: int
    ) -> List[RecommendationRecord]:
        latest_generation_stmt = (
            select(RecommendationGenerationModel.generation_id)
            .where(RecommendationGenerationModel.incident_id == incident_id)
            .order_by(RecommendationGenerationModel.created_at.desc())
            .limit(1)
        )
        latest_generation_result = await self.session.execute(latest_generation_stmt)
        latest_generation_id = latest_generation_result.scalar_one_or_none()
        if latest_generation_id is None:
            return []

        return await self.list_by_generation(latest_generation_id, limit=limit, offset=offset)
