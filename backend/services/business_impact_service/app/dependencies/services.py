import httpx
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.business_impact_service.app.core.config import settings
from backend.services.business_impact_service.app.repositories.business_impact_repository import (
    BusinessImpactRepository,
)
from backend.services.business_impact_service.app.repositories.incident_read_repository import (
    IncidentReadRepository,
)
from backend.services.business_impact_service.app.repositories.root_cause_read_repository import (
    RootCauseReadRepository,
)
from backend.services.business_impact_service.app.services.business_impact_application_service import (
    BusinessImpactApplicationService,
)
from backend.services.business_impact_service.app.services.business_impact_event_publisher import (
    BusinessImpactEventPublisher,
)
from backend.services.business_impact_service.app.services.impact_engine import BusinessImpactEngine, default_rules
from backend.shared.database.session import get_db_session


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Returns the one shared AsyncClient created for the app's lifetime (see main.py's lifespan) -- never one per request."""
    return request.app.state.http_client


def get_business_impact_event_publisher(
    client: httpx.AsyncClient = Depends(get_http_client),
) -> BusinessImpactEventPublisher:
    """Provides a configured BusinessImpactEventPublisher instance (Part 6)."""
    return BusinessImpactEventPublisher(
        client,
        recommendation_url=settings.RECOMMENDATION_SERVICE_URL,
        evaluation_url=settings.EVALUATION_SERVICE_URL,
        timeout_seconds=settings.EVENT_DELIVERY_TIMEOUT_SECONDS,
    )


def get_incident_read_repository(
    session: AsyncSession = Depends(get_db_session),
) -> IncidentReadRepository:
    """Provides a configured IncidentReadRepository instance."""
    return IncidentReadRepository(session)


def get_root_cause_read_repository(
    session: AsyncSession = Depends(get_db_session),
) -> RootCauseReadRepository:
    """Provides a configured RootCauseReadRepository instance."""
    return RootCauseReadRepository(session)


def get_business_impact_repository(
    session: AsyncSession = Depends(get_db_session),
) -> BusinessImpactRepository:
    """Provides a configured BusinessImpactRepository instance."""
    return BusinessImpactRepository(session)


def get_business_impact_engine() -> BusinessImpactEngine:
    """Provides a BusinessImpactEngine instance. Stateless and frozen (Phase 7 Step 1) -- no DB access."""
    return BusinessImpactEngine(rules=default_rules())


def get_business_impact_application_service(
    incident_read_repository: IncidentReadRepository = Depends(get_incident_read_repository),
    root_cause_read_repository: RootCauseReadRepository = Depends(get_root_cause_read_repository),
    business_impact_repository: BusinessImpactRepository = Depends(get_business_impact_repository),
    engine: BusinessImpactEngine = Depends(get_business_impact_engine),
    event_publisher: BusinessImpactEventPublisher = Depends(get_business_impact_event_publisher),
) -> BusinessImpactApplicationService:
    """Provides a configured BusinessImpactApplicationService instance, wired to publish BusinessImpactCompleted (Part 6)."""
    return BusinessImpactApplicationService(
        incident_read_repository, root_cause_read_repository, business_impact_repository, engine, event_publisher
    )
