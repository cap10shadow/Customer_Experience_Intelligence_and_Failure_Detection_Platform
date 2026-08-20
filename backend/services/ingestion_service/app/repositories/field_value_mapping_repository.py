import uuid
from datetime import datetime, timezone
from typing import Iterable, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.ingestion_service.app.models.field_value_mapping import FieldValueMapping
from backend.services.ingestion_service.app.models.field_value_mapping_occurrence_session import (
    FieldValueMappingOccurrenceSession,
)
from backend.shared.constants.enums.field_mapping import (
    FieldValueMappingConfidence,
    FieldValueMappingStatus,
    FieldValueMappingType,
)


class FieldValueMappingRepository:
    """
    Persistence for FieldValueMapping and its occurrence-session ledger.

    Architectural boundary: this repository never decides classification
    or approval -- it only stores/retrieves what mapping_service.py and
    the field-mappings API tell it to. In particular, only
    `set_approved`/`set_rejected` may write `status`/`target_value`;
    every other write method here (`create`, `update_confidence_and_suggestion`,
    `record_occurrence`) only ever touches a PENDING row's
    confidence/suggestion/occurrence bookkeeping.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    async def bulk_get_by_field(
        self, field_name: str, normalized_values: Iterable[str]
    ) -> dict[str, FieldValueMapping]:
        """One query: every existing mapping row for this field whose raw_value_normalized is in the given set."""
        values = list(normalized_values)
        if not values:
            return {}
        stmt = select(FieldValueMapping).where(
            FieldValueMapping.field_name == field_name,
            FieldValueMapping.raw_value_normalized.in_(values),
        )
        result = await self.session.execute(stmt)
        return {row.raw_value_normalized: row for row in result.scalars().all()}

    async def get_by_id(self, mapping_id: uuid.UUID) -> Optional[FieldValueMapping]:
        stmt = select(FieldValueMapping).where(FieldValueMapping.id == mapping_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Classifier-only writes -- PENDING rows, never status/target_value
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        field_name: str,
        raw_value_normalized: str,
        raw_value_original_example: str,
        confidence: FieldValueMappingConfidence,
        suggested_target_value: Optional[str],
        first_seen_dataset_id: Optional[uuid.UUID] = None,
    ) -> FieldValueMapping:
        """Inserts a new PENDING mapping row. Only ever called by the classifier for a value it has never seen before."""
        mapping = FieldValueMapping(
            field_name=field_name,
            raw_value_normalized=raw_value_normalized,
            raw_value_original_example=raw_value_original_example,
            target_value=None,
            suggested_target_value=suggested_target_value,
            confidence=confidence,
            mapping_type=None,
            status=FieldValueMappingStatus.PENDING,
            occurrence_count=0,
            first_seen_dataset_id=first_seen_dataset_id,
        )
        self.session.add(mapping)
        await self.session.flush()
        return mapping

    async def update_confidence_and_suggestion(
        self, mapping_id: uuid.UUID, *, confidence: FieldValueMappingConfidence, suggested_target_value: str
    ) -> Optional[FieldValueMapping]:
        """
        PENDING-only re-evaluation: upgrades a PENDING LOW row to MEDIUM
        with a freshly-registry-sourced suggestion. Never touches
        status/target_value -- callers (mapping_service) only invoke this
        for rows already confirmed PENDING.
        """
        mapping = await self.get_by_id(mapping_id)
        if mapping is None or mapping.status != FieldValueMappingStatus.PENDING:
            return mapping
        mapping.confidence = confidence
        mapping.suggested_target_value = suggested_target_value
        await self.session.flush()
        return mapping

    async def record_occurrence(
        self, mapping_id: uuid.UUID, analysis_session_id: uuid.UUID, row_count: int
    ) -> None:
        """
        Idempotent per (mapping_id, analysis_session_id): re-analyzing the
        same upload/session is a no-op here, a genuinely new session
        contributes its row_count exactly once. See
        FieldValueMappingOccurrenceSession's docstring for the full
        rationale (correction 1 of the approved plan).
        """
        insert_stmt = (
            pg_insert(FieldValueMappingOccurrenceSession)
            .values(mapping_id=mapping_id, analysis_session_id=analysis_session_id, row_count=row_count)
            .on_conflict_do_nothing(
                index_elements=["mapping_id", "analysis_session_id"],
            )
            .returning(FieldValueMappingOccurrenceSession.id)
        )
        result = await self.session.execute(insert_stmt)
        inserted_id = result.scalar_one_or_none()
        if inserted_id is None:
            # This exact session already contributed to this mapping -- no-op.
            return
        mapping = await self.get_by_id(mapping_id)
        if mapping is not None:
            mapping.occurrence_count += row_count
        await self.session.flush()

    # ------------------------------------------------------------------
    # Human-decision-only writes -- the only place status/target_value change
    # ------------------------------------------------------------------

    async def set_approved(
        self,
        mapping_id: uuid.UUID,
        *,
        target_value: str,
        mapping_type: FieldValueMappingType,
        reviewed_by: Optional[str],
    ) -> Optional[FieldValueMapping]:
        mapping = await self.get_by_id(mapping_id)
        if mapping is None:
            return None
        mapping.target_value = target_value
        mapping.mapping_type = mapping_type
        mapping.status = FieldValueMappingStatus.APPROVED
        mapping.reviewed_by = reviewed_by
        mapping.reviewed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return mapping

    async def set_rejected(self, mapping_id: uuid.UUID, *, reviewed_by: Optional[str]) -> Optional[FieldValueMapping]:
        mapping = await self.get_by_id(mapping_id)
        if mapping is None:
            return None
        mapping.status = FieldValueMappingStatus.REJECTED
        mapping.reviewed_by = reviewed_by
        mapping.reviewed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return mapping

    # ------------------------------------------------------------------
    # Review-queue listings
    # ------------------------------------------------------------------

    async def list_pending(
        self,
        field_name: str,
        confidence: Optional[FieldValueMappingConfidence] = None,
        skip: int = 0,
        limit: int = 25,
    ) -> Sequence[FieldValueMapping]:
        stmt = select(FieldValueMapping).where(
            FieldValueMapping.field_name == field_name,
            FieldValueMapping.status == FieldValueMappingStatus.PENDING,
        )
        if confidence is not None:
            stmt = stmt.where(FieldValueMapping.confidence == confidence)
        stmt = stmt.order_by(FieldValueMapping.occurrence_count.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_pending(self, field_name: str, confidence: Optional[FieldValueMappingConfidence] = None) -> int:
        stmt = select(func.count(FieldValueMapping.id)).where(
            FieldValueMapping.field_name == field_name,
            FieldValueMapping.status == FieldValueMappingStatus.PENDING,
        )
        if confidence is not None:
            stmt = stmt.where(FieldValueMapping.confidence == confidence)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def list_approved(self, field_name: str, skip: int = 0, limit: int = 25) -> Sequence[FieldValueMapping]:
        stmt = (
            select(FieldValueMapping)
            .where(
                FieldValueMapping.field_name == field_name,
                FieldValueMapping.status == FieldValueMappingStatus.APPROVED,
            )
            .order_by(FieldValueMapping.raw_value_normalized)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_approved(self, field_name: str) -> int:
        stmt = select(func.count(FieldValueMapping.id)).where(
            FieldValueMapping.field_name == field_name,
            FieldValueMapping.status == FieldValueMappingStatus.APPROVED,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
