"""
In-memory fakes for FieldValueMappingRepository / FieldAliasSuggestionRepository.

Faithfully replicates the real repository's invariants (unique
(field_name, raw_value_normalized), idempotent occurrence recording per
(mapping_id, analysis_session_id), and the PENDING-only guard on
update_confidence_and_suggestion) without a live database -- matching
this codebase's existing convention of mock/fake-repository unit tests
(see tests/test_api_complaints.py) rather than a live-DB pytest fixture,
which no service in this repo uses.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from backend.shared.constants.enums.field_mapping import (
    FieldValueMappingConfidence,
    FieldValueMappingStatus,
    FieldValueMappingType,
)


@dataclass
class FakeMappingRow:
    id: uuid.UUID
    field_name: str
    raw_value_normalized: str
    raw_value_original_example: str
    confidence: FieldValueMappingConfidence
    suggested_target_value: Optional[str] = None
    target_value: Optional[str] = None
    mapping_type: Optional[FieldValueMappingType] = None
    status: FieldValueMappingStatus = FieldValueMappingStatus.PENDING
    occurrence_count: int = 0
    first_seen_dataset_id: Optional[uuid.UUID] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    inserted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FakeFieldValueMappingRepository:
    def __init__(self):
        self.rows: dict[uuid.UUID, FakeMappingRow] = {}
        self._occurrence_sessions: set[tuple[uuid.UUID, uuid.UUID]] = set()

    async def bulk_get_by_field(self, field_name, normalized_values):
        values = set(normalized_values)
        return {
            row.raw_value_normalized: row
            for row in self.rows.values()
            if row.field_name == field_name and row.raw_value_normalized in values
        }

    async def get_by_id(self, mapping_id):
        return self.rows.get(mapping_id)

    async def create(
        self,
        *,
        field_name,
        raw_value_normalized,
        raw_value_original_example,
        confidence,
        suggested_target_value,
        first_seen_dataset_id=None,
    ):
        for row in self.rows.values():
            if row.field_name == field_name and row.raw_value_normalized == raw_value_normalized:
                raise ValueError("uq_field_value_mappings_field_raw violated")
        row = FakeMappingRow(
            id=uuid.uuid4(),
            field_name=field_name,
            raw_value_normalized=raw_value_normalized,
            raw_value_original_example=raw_value_original_example,
            confidence=confidence,
            suggested_target_value=suggested_target_value,
            first_seen_dataset_id=first_seen_dataset_id,
        )
        self.rows[row.id] = row
        return row

    async def update_confidence_and_suggestion(self, mapping_id, *, confidence, suggested_target_value):
        row = self.rows.get(mapping_id)
        if row is None or row.status != FieldValueMappingStatus.PENDING:
            return row
        row.confidence = confidence
        row.suggested_target_value = suggested_target_value
        return row

    async def record_occurrence(self, mapping_id, analysis_session_id, row_count):
        key = (mapping_id, analysis_session_id)
        if key in self._occurrence_sessions:
            return
        self._occurrence_sessions.add(key)
        row = self.rows.get(mapping_id)
        if row is not None:
            row.occurrence_count += row_count

    async def set_approved(self, mapping_id, *, target_value, mapping_type, reviewed_by):
        row = self.rows.get(mapping_id)
        if row is None:
            return None
        row.target_value = target_value
        row.mapping_type = mapping_type
        row.status = FieldValueMappingStatus.APPROVED
        row.reviewed_by = reviewed_by
        row.reviewed_at = datetime.now(timezone.utc)
        return row

    async def set_rejected(self, mapping_id, *, reviewed_by):
        row = self.rows.get(mapping_id)
        if row is None:
            return None
        row.status = FieldValueMappingStatus.REJECTED
        row.reviewed_by = reviewed_by
        row.reviewed_at = datetime.now(timezone.utc)
        return row

    async def list_pending(self, field_name, confidence=None, skip=0, limit=25):
        rows = [
            r
            for r in self.rows.values()
            if r.field_name == field_name
            and r.status == FieldValueMappingStatus.PENDING
            and (confidence is None or r.confidence == confidence)
        ]
        rows.sort(key=lambda r: r.occurrence_count, reverse=True)
        return rows[skip : skip + limit]

    async def count_pending(self, field_name, confidence=None):
        return len(await self.list_pending(field_name, confidence=confidence, skip=0, limit=10_000_000))

    async def list_approved(self, field_name, skip=0, limit=25):
        rows = [
            r
            for r in self.rows.values()
            if r.field_name == field_name and r.status == FieldValueMappingStatus.APPROVED
        ]
        rows.sort(key=lambda r: r.raw_value_normalized)
        return rows[skip : skip + limit]

    async def count_approved(self, field_name):
        return len(await self.list_approved(field_name, skip=0, limit=10_000_000))


@dataclass
class FakeAliasSuggestionRow:
    id: uuid.UUID
    field_name: str
    source_value_normalized: str
    suggested_target_value: str
    notes: Optional[str] = None
    created_by: Optional[str] = None
    inserted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FakeFieldAliasSuggestionRepository:
    def __init__(self):
        self.rows: dict[uuid.UUID, FakeAliasSuggestionRow] = {}

    async def bulk_get_by_field(self, field_name, normalized_values):
        values = set(normalized_values)
        return {
            row.source_value_normalized: row.suggested_target_value
            for row in self.rows.values()
            if row.field_name == field_name and row.source_value_normalized in values
        }

    async def get_by_field_and_source(self, field_name, source_value_normalized):
        for row in self.rows.values():
            if row.field_name == field_name and row.source_value_normalized == source_value_normalized:
                return row
        return None

    async def get_by_id(self, suggestion_id):
        return self.rows.get(suggestion_id)

    async def create(self, suggestion):
        row = FakeAliasSuggestionRow(
            id=uuid.uuid4(),
            field_name=suggestion.field_name,
            source_value_normalized=suggestion.source_value_normalized,
            suggested_target_value=suggestion.suggested_target_value,
            notes=suggestion.notes,
            created_by=suggestion.created_by,
        )
        self.rows[row.id] = row
        return row

    async def update_target(self, suggestion_id, *, suggested_target_value):
        row = self.rows.get(suggestion_id)
        if row is None:
            return None
        row.suggested_target_value = suggested_target_value
        return row

    async def list_by_field(self, field_name, skip=0, limit=25):
        rows = [r for r in self.rows.values() if r.field_name == field_name]
        rows.sort(key=lambda r: r.source_value_normalized)
        return rows[skip : skip + limit]
