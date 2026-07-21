from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database.session import get_db_session
from backend.services.root_cause_service.app.repositories.incident_read_repository import IncidentReadRepository
from backend.services.root_cause_service.app.repositories.root_cause_repository import RootCauseRepository
from backend.services.root_cause_service.app.services.root_cause_application_service import RootCauseApplicationService
from backend.services.root_cause_service.app.services.root_cause_engine import RootCauseEngine


def get_incident_read_repository(
    session: AsyncSession = Depends(get_db_session)
) -> IncidentReadRepository:
    """Provides a configured IncidentReadRepository instance."""
    return IncidentReadRepository(session)


def get_root_cause_repository(
    session: AsyncSession = Depends(get_db_session)
) -> RootCauseRepository:
    """Provides a configured RootCauseRepository instance."""
    return RootCauseRepository(session)


def get_root_cause_engine() -> RootCauseEngine:
    """Provides a RootCauseEngine instance. Stateless and frozen (Phase 6 Step 1) — no DB access."""
    return RootCauseEngine()


def get_root_cause_application_service(
    incident_read_repository: IncidentReadRepository = Depends(get_incident_read_repository),
    root_cause_repository: RootCauseRepository = Depends(get_root_cause_repository),
    engine: RootCauseEngine = Depends(get_root_cause_engine),
) -> RootCauseApplicationService:
    """Provides a configured RootCauseApplicationService instance."""
    return RootCauseApplicationService(incident_read_repository, root_cause_repository, engine)
