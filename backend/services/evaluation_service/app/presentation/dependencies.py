from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.evaluation_service.app.application.evaluation_statistics_service import (
    EvaluationStatisticsService,
)
from backend.services.evaluation_service.app.domain.evaluation_repository import EvaluationRepository
from backend.services.evaluation_service.app.infrastructure.persistence.repositories.postgresql_evaluation_repository import (
    PostgreSQLEvaluationRepository,
)
from backend.shared.database.session import get_db_session


def get_evaluation_repository(session: AsyncSession = Depends(get_db_session)) -> EvaluationRepository:
    """
    Provides a configured EvaluationRepository instance.

    Dependency Inversion in practice: this is the one place the concrete
    `PostgreSQLEvaluationRepository` is constructed. Every consumer (the
    API routes, `EvaluationStatisticsService`, and -- once wired in a
    future step -- `EvaluationOrchestrator`) depends only on the
    `EvaluationRepository` interface.
    """
    return PostgreSQLEvaluationRepository(session)


def get_evaluation_statistics_service(
    repository: EvaluationRepository = Depends(get_evaluation_repository),
) -> EvaluationStatisticsService:
    """Provides a configured EvaluationStatisticsService instance."""
    return EvaluationStatisticsService(repository)
