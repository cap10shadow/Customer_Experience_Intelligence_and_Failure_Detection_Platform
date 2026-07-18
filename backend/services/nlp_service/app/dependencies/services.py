from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database.session import get_db_session
from backend.services.nlp_service.app.repositories.complaint_enrichment_repository import EnrichmentRepository
from backend.services.nlp_service.app.services.enrichment_service import EnrichmentService


def get_enrichment_repository(
    session: AsyncSession = Depends(get_db_session)
) -> EnrichmentRepository:
    """Provides a configured EnrichmentRepository instance."""
    return EnrichmentRepository(session)


def get_enrichment_service(
    repository: EnrichmentRepository = Depends(get_enrichment_repository)
) -> EnrichmentService:
    """Provides a configured EnrichmentService instance."""
    return EnrichmentService(repository)
