from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.evaluation_service.app.application.evaluation_orchestrator import EvaluationOrchestrator
from backend.services.evaluation_service.app.application.evaluation_statistics_service import (
    EvaluationStatisticsService,
)
from backend.services.evaluation_service.app.application.lifecycle.evaluation_lifecycle_service import (
    EvaluationLifecycleService,
)
from backend.services.evaluation_service.app.application.ports.event_publisher import EventPublisher
from backend.services.evaluation_service.app.domain.confidence_analyzer import ConfidenceAnalyzer
from backend.services.evaluation_service.app.domain.evaluation_builder import EvaluationBuilder
from backend.services.evaluation_service.app.domain.evaluation_repository import EvaluationRepository
from backend.services.evaluation_service.app.domain.explainability_engine import ExplainabilityEngine
from backend.services.evaluation_service.app.domain.quality_engine import QualityEngine
from backend.services.evaluation_service.app.domain.validation_engine import ValidationEngine
from backend.services.evaluation_service.app.infrastructure.messaging.consumers.business_impact_completed_consumer import (
    BusinessImpactCompletedConsumer,
)
from backend.services.evaluation_service.app.infrastructure.messaging.publishers.in_process_event_publisher import (
    InProcessEventPublisher,
)
from backend.services.evaluation_service.app.infrastructure.persistence.repositories.postgresql_evaluation_repository import (
    PostgreSQLEvaluationRepository,
)
from backend.shared.database.database import async_session_maker
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


def get_event_publisher() -> EventPublisher:
    """Provides a configured EventPublisher instance (Phase 8 Step 3)."""
    return InProcessEventPublisher()


def get_evaluation_lifecycle_service() -> EvaluationLifecycleService:
    """
    Provides a configured EvaluationLifecycleService instance (Phase 8 Step 3).

    Unlike `get_evaluation_repository` (bound to one FastAPI-request-scoped
    session via `get_db_session`), this service owns its own transaction
    boundary end to end -- it is handed `async_session_maker` itself, not
    an already-open session, and opens/commits/rolls back a fresh session
    per `execute()` call. `repository_factory`/`orchestrator_factory` keep
    Dependency Inversion intact: the service depends only on the
    `EvaluationRepository`/`EvaluationOrchestrator` abstractions, this is
    simply where their concrete implementations are wired in, exactly as
    `get_evaluation_repository` already does for the REST API.
    """
    return EvaluationLifecycleService(
        session_factory=async_session_maker,
        repository_factory=lambda session: PostgreSQLEvaluationRepository(session),
        orchestrator_factory=lambda repository: EvaluationOrchestrator(
            validation_engine=ValidationEngine(),
            quality_engine=QualityEngine(),
            explainability_engine=ExplainabilityEngine(),
            confidence_analyzer=ConfidenceAnalyzer(),
            evaluation_builder=EvaluationBuilder(),
            repository=repository,
        ),
        event_publisher=get_event_publisher(),
    )


def get_business_impact_completed_consumer(
    lifecycle_service: EvaluationLifecycleService = Depends(get_evaluation_lifecycle_service),
) -> BusinessImpactCompletedConsumer:
    """Provides a configured BusinessImpactCompletedConsumer instance (Phase 8 Step 3)."""
    return BusinessImpactCompletedConsumer(lifecycle_service)
