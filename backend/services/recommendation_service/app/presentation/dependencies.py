from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.recommendation_service.app.application.lifecycle.recommendation_lifecycle_service import (
    RecommendationLifecycleService,
)
from backend.services.recommendation_service.app.application.orchestration.recommendation_orchestrator import (
    RecommendationOrchestrator,
)
from backend.services.recommendation_service.app.application.ports.recommendation_event_publisher import (
    RecommendationEventPublisher,
)
from backend.services.recommendation_service.app.application.recommendation_statistics_service import (
    RecommendationStatisticsService,
)
from backend.services.recommendation_service.app.domain.recommendation_engine import RecommendationEngine, default_rules
from backend.services.recommendation_service.app.domain.recommendation_repository import RecommendationRepository
from backend.services.recommendation_service.app.infrastructure.messaging.consumers.business_impact_completed_consumer import (
    BusinessImpactCompletedConsumer,
)
from backend.services.recommendation_service.app.infrastructure.messaging.publishers.in_process_recommendation_event_publisher import (
    InProcessRecommendationEventPublisher,
)
from backend.services.recommendation_service.app.infrastructure.persistence.repositories.postgresql_recommendation_repository import (
    PostgreSQLRecommendationRepository,
)
from backend.shared.database.database import async_session_maker
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


def get_recommendation_event_publisher() -> RecommendationEventPublisher:
    """Provides a configured RecommendationEventPublisher instance (Phase 9 Step 3)."""
    return InProcessRecommendationEventPublisher()


def get_recommendation_lifecycle_service() -> RecommendationLifecycleService:
    """
    Provides a configured RecommendationLifecycleService instance (Phase 9 Step 3).

    Unlike `get_recommendation_repository` (bound to one FastAPI-request-scoped
    session via `get_db_session`), this service owns its own transaction
    boundary end to end -- it is handed `async_session_maker` itself, not
    an already-open session, and opens/commits/rolls back a fresh session
    per `execute()` call. The same shape `evaluation_service`'s
    `get_evaluation_lifecycle_service` already established.
    `repository_factory`/`orchestrator_factory` keep Dependency Inversion
    intact: the service depends only on the
    `RecommendationRepository`/`RecommendationOrchestrator` abstractions,
    this is simply where their concrete implementations are wired in,
    exactly as `get_recommendation_repository` already does for the REST API.
    """
    return RecommendationLifecycleService(
        session_factory=async_session_maker,
        repository_factory=lambda session: PostgreSQLRecommendationRepository(session),
        orchestrator_factory=lambda repository: RecommendationOrchestrator(
            engine=RecommendationEngine(rules=default_rules()),
            repository=repository,
        ),
        event_publisher=get_recommendation_event_publisher(),
    )


def get_business_impact_completed_consumer(
    lifecycle_service: RecommendationLifecycleService = Depends(get_recommendation_lifecycle_service),
) -> BusinessImpactCompletedConsumer:
    """Provides a configured BusinessImpactCompletedConsumer instance (Phase 9 Step 3)."""
    return BusinessImpactCompletedConsumer(lifecycle_service)
