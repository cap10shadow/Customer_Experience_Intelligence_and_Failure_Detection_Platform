import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.evaluation_service.app.domain.evaluation import Evaluation
from backend.services.evaluation_service.app.domain.evaluation_record import EvaluationRecord
from backend.services.evaluation_service.app.domain.evaluation_repository import EvaluationRepository
from backend.services.evaluation_service.app.infrastructure.persistence.models.evaluation_model import EvaluationModel
from backend.services.evaluation_service.app.infrastructure.persistence.repositories.evaluation_model_mapper import (
    EvaluationModelMapper,
)


class PostgreSQLEvaluationRepository(EvaluationRepository):
    """
    PostgreSQL Evaluation Repository

    Ownership:
    Owned by the Evaluation Service's infrastructure layer.

    Operational Purpose:
    Concrete, PostgreSQL/SQLAlchemy implementation of the Domain-defined
    `EvaluationRepository` port. Responsible strictly for database
    persistence and retrieval -- no business logic, no scoring, no engine
    execution.

    Architectural Boundaries:
    - Evaluations are immutable and append-only: this class exposes no
      update or delete operation, and never issues an UPDATE/DELETE against
      `evaluations`.
    - `save()` determines `previous_evaluation_id` itself, by looking up
      the current latest record for the same incident before inserting --
      this is persistence/lineage bookkeeping (comparable to a database
      assigning a primary key or a version counter), not a business rule.
    - `root_cause_id` / `business_impact_id` are always persisted as NULL
      here: neither is available on the `Evaluation` this repository is
      handed (see `EvaluationRecord`'s docstring for why).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, evaluation: Evaluation) -> EvaluationRecord:
        latest = await self._get_latest_model(evaluation.incident_id)
        previous_evaluation_id = latest.evaluation_id if latest is not None else None

        model = EvaluationModelMapper.to_orm(
            evaluation,
            previous_evaluation_id=previous_evaluation_id,
            root_cause_id=None,
            business_impact_id=None,
        )
        self.session.add(model)
        await self.session.flush()
        return EvaluationModelMapper.to_domain(model)

    async def get_by_id(self, evaluation_id: uuid.UUID) -> Optional[EvaluationRecord]:
        stmt = select(EvaluationModel).where(EvaluationModel.evaluation_id == evaluation_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return EvaluationModelMapper.to_domain(model) if model is not None else None

    async def get_latest(self, incident_id: str) -> Optional[EvaluationRecord]:
        model = await self._get_latest_model(incident_id)
        return EvaluationModelMapper.to_domain(model) if model is not None else None

    async def list_by_incident(
        self, incident_id: Optional[str] = None, *, limit: int, offset: int
    ) -> List[EvaluationRecord]:
        stmt = select(EvaluationModel)
        if incident_id is not None:
            stmt = stmt.where(EvaluationModel.incident_id == incident_id)
        stmt = stmt.order_by(EvaluationModel.created_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        return [EvaluationModelMapper.to_domain(model) for model in result.scalars().all()]

    async def list_history(self, incident_id: str, *, limit: int, offset: int) -> List[EvaluationRecord]:
        stmt = (
            select(EvaluationModel)
            .where(EvaluationModel.incident_id == incident_id)
            .order_by(EvaluationModel.evaluation_version.desc(), EvaluationModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return [EvaluationModelMapper.to_domain(model) for model in result.scalars().all()]

    async def _get_latest_model(self, incident_id: str) -> Optional[EvaluationModel]:
        """
        Shared lookup used by both `get_latest()` and `save()` (to
        determine `previous_evaluation_id`) -- ordered by
        `evaluation_version` then `created_at`, using the same composite
        index (`incident_id`, `evaluation_version DESC`) both queries rely on.
        """
        stmt = (
            select(EvaluationModel)
            .where(EvaluationModel.incident_id == incident_id)
            .order_by(EvaluationModel.evaluation_version.desc(), EvaluationModel.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
