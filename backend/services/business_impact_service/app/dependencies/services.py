from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

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
from backend.services.business_impact_service.app.services.impact_engine import BusinessImpactEngine, default_rules
from backend.shared.database.session import get_db_session


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
) -> BusinessImpactApplicationService:
    """Provides a configured BusinessImpactApplicationService instance."""
    return BusinessImpactApplicationService(
        incident_read_repository, root_cause_read_repository, business_impact_repository, engine
    )
