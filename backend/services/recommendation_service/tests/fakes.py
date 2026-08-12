"""
Shared, in-memory test support for Phase 9 Step 2 (Persistence & APIs) and
Step 3 (Execution Lifecycle).

Not a test module itself (no `test_` prefix -- pytest will not collect it).

`FakeRecommendationRepository` implements the exact same `RecommendationRepository`
contract `PostgreSQLRecommendationRepository` does -- including computing
duplicate-`event_id` rejection in `save_many()`, the same repository
responsibility documented on the real implementation -- so tests built
against it exercise real API routing / statistics / lifecycle logic
faithfully without a database.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence

from backend.services.recommendation_service.app.domain.recommendation import Recommendation
from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_decision import RecommendationDecision
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.recommendation_record import RecommendationRecord
from backend.services.recommendation_service.app.domain.recommendation_repository import (
    DuplicateGenerationEventError,
    RecommendationRepository,
)


class FakeRecommendationRepository(RecommendationRepository):
    """In-memory stand-in for PostgreSQLRecommendationRepository -- same async contract, no database."""

    def __init__(self) -> None:
        self.by_id: Dict[uuid.UUID, RecommendationRecord] = {}
        # incident_id -> ordered list of (generation_id, created_at), most recent last.
        self.generations_by_incident: Dict[str, List[tuple]] = {}
        # event_id -> generation_id, mirroring the real UNIQUE(event_id) constraint.
        self.generation_by_event_id: Dict[uuid.UUID, uuid.UUID] = {}

    async def save_many(
        self,
        recommendations: Sequence[Recommendation],
        *,
        incident_id: str,
        generation_id: uuid.UUID,
        event_id: Optional[uuid.UUID] = None,
    ) -> List[RecommendationRecord]:
        if event_id is not None and event_id in self.generation_by_event_id:
            raise DuplicateGenerationEventError(f"A RecommendationGeneration for event_id={event_id} already exists")

        generation_created_at = datetime.now(timezone.utc)
        self.generations_by_incident.setdefault(incident_id, []).append((generation_id, generation_created_at))
        if event_id is not None:
            self.generation_by_event_id[event_id] = generation_id

        records = []
        for recommendation in recommendations:
            record = RecommendationRecord(
                recommendation_id=uuid.uuid4(),
                recommendation=recommendation,
                generation_id=generation_id,
                created_at=datetime.now(timezone.utc),
            )
            self.by_id[record.recommendation_id] = record
            records.append(record)
        return records

    async def get_generation_by_event_id(self, event_id: uuid.UUID) -> Optional[uuid.UUID]:
        return self.generation_by_event_id.get(event_id)

    async def get_by_id(self, recommendation_id: uuid.UUID) -> Optional[RecommendationRecord]:
        return self.by_id.get(recommendation_id)

    async def list_by_incident(
        self, incident_id: Optional[str] = None, *, limit: int, offset: int
    ) -> List[RecommendationRecord]:
        records = list(self.by_id.values())
        if incident_id is not None:
            records = [record for record in records if record.recommendation.incident_id == incident_id]
        records.sort(key=lambda record: record.created_at, reverse=True)
        return records[offset : offset + limit]

    async def list_by_generation(self, generation_id: uuid.UUID, *, limit: int, offset: int) -> List[RecommendationRecord]:
        records = [record for record in self.by_id.values() if record.generation_id == generation_id]
        records.sort(key=lambda record: record.created_at, reverse=True)
        return records[offset : offset + limit]

    async def list_by_category(
        self, category: RecommendationCategory, *, limit: int, offset: int
    ) -> List[RecommendationRecord]:
        records = [record for record in self.by_id.values() if record.recommendation.category == category]
        records.sort(key=lambda record: record.created_at, reverse=True)
        return records[offset : offset + limit]

    async def list_by_priority(
        self, priority: RecommendationPriority, *, limit: int, offset: int
    ) -> List[RecommendationRecord]:
        records = [record for record in self.by_id.values() if record.recommendation.priority == priority]
        records.sort(key=lambda record: record.created_at, reverse=True)
        return records[offset : offset + limit]

    async def get_latest_by_incident(self, incident_id: str, *, limit: int, offset: int) -> List[RecommendationRecord]:
        generations = self.generations_by_incident.get(incident_id, [])
        if not generations:
            return []
        latest_generation_id = max(generations, key=lambda item: item[1])[0]
        return await self.list_by_generation(latest_generation_id, limit=limit, offset=offset)

    async def update_decision(
        self,
        recommendation_id: uuid.UUID,
        *,
        decision: RecommendationDecision,
        note: Optional[str],
        decided_at: datetime,
    ) -> Optional[RecommendationRecord]:
        existing = self.by_id.get(recommendation_id)
        if existing is None:
            return None

        updated = RecommendationRecord(
            recommendation_id=existing.recommendation_id,
            recommendation=existing.recommendation,
            generation_id=existing.generation_id,
            created_at=existing.created_at,
            decision=decision,
            decision_note=note,
            decided_at=decided_at,
        )
        self.by_id[recommendation_id] = updated
        return updated
