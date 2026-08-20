from typing import Annotated

from fastapi import Depends

from backend.services.ingestion_service.app.repositories.complaint_repository import ComplaintRepository
from backend.services.ingestion_service.app.repositories.dataset_repository import DatasetRepository
from backend.services.ingestion_service.app.repositories.field_alias_suggestion_repository import (
    FieldAliasSuggestionRepository,
)
from backend.services.ingestion_service.app.repositories.field_value_mapping_repository import (
    FieldValueMappingRepository,
)
from backend.shared.database.session import DbSession


def get_complaint_repository(session: DbSession) -> ComplaintRepository:
    """Provides a configured ComplaintRepository instance."""
    return ComplaintRepository(session)


def get_dataset_repository(session: DbSession) -> DatasetRepository:
    """Provides a configured DatasetRepository instance."""
    return DatasetRepository(session)


def get_field_value_mapping_repository(session: DbSession) -> FieldValueMappingRepository:
    """Provides a configured FieldValueMappingRepository instance."""
    return FieldValueMappingRepository(session)


def get_field_alias_suggestion_repository(session: DbSession) -> FieldAliasSuggestionRepository:
    """Provides a configured FieldAliasSuggestionRepository instance."""
    return FieldAliasSuggestionRepository(session)


ComplaintRepo = Annotated[ComplaintRepository, Depends(get_complaint_repository)]
DatasetRepo = Annotated[DatasetRepository, Depends(get_dataset_repository)]
FieldValueMappingRepo = Annotated[FieldValueMappingRepository, Depends(get_field_value_mapping_repository)]
FieldAliasSuggestionRepo = Annotated[
    FieldAliasSuggestionRepository, Depends(get_field_alias_suggestion_repository)
]
