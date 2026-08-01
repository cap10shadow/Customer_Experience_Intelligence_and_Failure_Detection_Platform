from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.recommendation_service.app.application.recommendation_statistics_service import (
    RecommendationStatisticsService,
)
from backend.services.recommendation_service.app.domain.recommendation_repository import RecommendationRepository
from backend.services.recommendation_service.app.infrastructure.persistence.repositories.postgresql_recommendation_repository import (
    PostgreSQLRecommendationRepository,
)
from backend.shared.database.session import get_db_session


def get_recommendation_repository(session: AsyncSession = Depends(get_db_session)) -> RecommendationRepository:
    """
    Provides a configured RecommendationRepository instance.

    Dependency Inversion in practice: this is the one place the concrete
    `PostgreSQLRecommendationRepository` is constructed. Every consumer
    (the API routes, `RecommendationStatisticsService`, and -- once wired
    in Step 3 -- the execution lifecycle) depends only on the
    `RecommendationRepository` interface. The same convention already
    established by `evaluation_service`'s `get_evaluation_repository`.
    """
    return PostgreSQLRecommendationRepository(session)


def get_recommendation_statistics_service(
    repository: RecommendationRepository = Depends(get_recommendation_repository),
) -> RecommendationStatisticsService:
    """Provides a configured RecommendationStatisticsService instance."""
    return RecommendationStatisticsService(repository)
