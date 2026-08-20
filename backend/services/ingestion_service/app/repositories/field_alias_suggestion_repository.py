import uuid
from typing import Iterable, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.ingestion_service.app.models.field_alias_suggestion import FieldAliasSuggestion


class FieldAliasSuggestionRepository:
    """
    Persistence for the curated alias-suggestion registry.

    This is the ONLY repository whose rows the classifier is allowed to
    read but never write -- registry entries are created/updated
    exclusively via the /field-mappings/alias-suggestions endpoints,
    never inferred at runtime.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_get_by_field(self, field_name: str, normalized_values: Iterable[str]) -> dict[str, str]:
        """One query: normalized source value -> suggested_target_value, for every match in the given set."""
        values = list(normalized_values)
        if not values:
            return {}
        stmt = select(FieldAliasSuggestion).where(
            FieldAliasSuggestion.field_name == field_name,
            FieldAliasSuggestion.source_value_normalized.in_(values),
        )
        result = await self.session.execute(stmt)
        return {row.source_value_normalized: row.suggested_target_value for row in result.scalars().all()}

    async def get_by_field_and_source(
        self, field_name: str, source_value_normalized: str
    ) -> Optional[FieldAliasSuggestion]:
        stmt = select(FieldAliasSuggestion).where(
            FieldAliasSuggestion.field_name == field_name,
            FieldAliasSuggestion.source_value_normalized == source_value_normalized,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, suggestion_id: uuid.UUID) -> Optional[FieldAliasSuggestion]:
        stmt = select(FieldAliasSuggestion).where(FieldAliasSuggestion.id == suggestion_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, suggestion: FieldAliasSuggestion) -> FieldAliasSuggestion:
        self.session.add(suggestion)
        await self.session.flush()
        return suggestion

    async def update_target(self, suggestion_id: uuid.UUID, *, suggested_target_value: str) -> Optional[FieldAliasSuggestion]:
        suggestion = await self.get_by_id(suggestion_id)
        if suggestion is None:
            return None
        suggestion.suggested_target_value = suggested_target_value
        await self.session.flush()
        return suggestion

    async def list_by_field(self, field_name: str, skip: int = 0, limit: int = 25) -> Sequence[FieldAliasSuggestion]:
        stmt = (
            select(FieldAliasSuggestion)
            .where(FieldAliasSuggestion.field_name == field_name)
            .order_by(FieldAliasSuggestion.source_value_normalized)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
