from typing import Annotated

from fastapi import Depends

from backend.services.ingestion_service.app.dependencies.repositories import (
    FieldAliasSuggestionRepo,
    FieldValueMappingRepo,
)
from backend.services.ingestion_service.app.services.mapping_service import MappingService


def get_mapping_service(
    mapping_repo: FieldValueMappingRepo, alias_repo: FieldAliasSuggestionRepo
) -> MappingService:
    """Provides a configured MappingService instance."""
    return MappingService(mapping_repo, alias_repo)


MappingSvc = Annotated[MappingService, Depends(get_mapping_service)]
