from typing import Annotated

from fastapi import Depends

from backend.services.ingestion_service.app.repositories.complaint_repository import ComplaintRepository
from backend.shared.database.session import DbSession


def get_complaint_repository(session: DbSession) -> ComplaintRepository:
    """Provides a configured ComplaintRepository instance."""
    return ComplaintRepository(session)


ComplaintRepo = Annotated[ComplaintRepository, Depends(get_complaint_repository)]
