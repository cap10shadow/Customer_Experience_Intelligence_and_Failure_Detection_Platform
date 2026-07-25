"""
Shared, in-memory test support for Phase 8 Step 2 (Persistence & APIs).

Not a test module itself (no `test_` prefix -- pytest will not collect it).

`FakeEvaluationRepository` implements the exact same `EvaluationRepository`
contract `PostgreSQLEvaluationRepository` does -- including computing
`previous_evaluation_id` lineage in `save()`, the same repository
responsibility documented on the real implementation -- so tests built
against it exercise the real `EvaluationOrchestrator` / API routing logic
faithfully without a database.
"""

import uuid
from dataclasses import replace
from datetime import datetime, timezone
from typing import Dict, List, Optional

from backend.services.evaluation_service.app.domain.evaluation import Evaluation
from backend.services.evaluation_service.app.domain.evaluation_record import EvaluationRecord
from backend.services.evaluation_service.app.domain.evaluation_repository import EvaluationRepository


class FakeEvaluationRepository(EvaluationRepository):
    """In-memory stand-in for PostgreSQLEvaluationRepository -- same async contract, no database."""

    def __init__(self) -> None:
        self.by_id: Dict[uuid.UUID, EvaluationRecord] = {}

    async def save(self, evaluation: Evaluation) -> EvaluationRecord:
        latest = await self.get_latest(evaluation.incident_id)
        previous_evaluation_id = str(latest.evaluation_id) if latest is not None else None
        evaluation_with_lineage = replace(
            evaluation, metadata=replace(evaluation.metadata, previous_evaluation_id=previous_evaluation_id)
        )

        record = EvaluationRecord(
            evaluation_id=uuid.uuid4(),
            evaluation=evaluation_with_lineage,
            root_cause_id=None,
            business_impact_id=None,
            created_at=datetime.now(timezone.utc),
        )
        self.by_id[record.evaluation_id] = record
        return record

    async def get_by_id(self, evaluation_id: uuid.UUID) -> Optional[EvaluationRecord]:
        return self.by_id.get(evaluation_id)

    async def get_latest(self, incident_id: str) -> Optional[EvaluationRecord]:
        matches = [record for record in self.by_id.values() if record.evaluation.incident_id == incident_id]
        if not matches:
            return None
        return max(matches, key=lambda record: record.created_at)

    async def list_by_incident(
        self, incident_id: Optional[str] = None, *, limit: int, offset: int
    ) -> List[EvaluationRecord]:
        records = list(self.by_id.values())
        if incident_id is not None:
            records = [record for record in records if record.evaluation.incident_id == incident_id]
        records.sort(key=lambda record: record.created_at, reverse=True)
        return records[offset : offset + limit]

    async def list_history(self, incident_id: str, *, limit: int, offset: int) -> List[EvaluationRecord]:
        records = [record for record in self.by_id.values() if record.evaluation.incident_id == incident_id]
        records.sort(key=lambda record: record.created_at, reverse=True)
        return records[offset : offset + limit]
