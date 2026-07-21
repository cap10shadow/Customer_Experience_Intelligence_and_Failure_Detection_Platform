import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from backend.services.root_cause_service.app.mappers.incident_mapper import IncidentMapper
from backend.services.root_cause_service.app.mappers.root_cause_mapper import RootCauseMapper
from backend.services.root_cause_service.app.models.root_cause import RootCause
from backend.services.root_cause_service.app.repositories.incident_read_repository import IncidentReadRepository
from backend.services.root_cause_service.app.repositories.root_cause_repository import RootCauseRepository
from backend.services.root_cause_service.app.services.exceptions import (
    IncidentNotFoundError,
    RootCauseAlreadyExistsError,
    RootCauseNotFoundError,
)
from backend.services.root_cause_service.app.services.lifecycle_validator import LifecycleValidator
from backend.services.root_cause_service.app.services.root_cause_engine import RootCauseEngine
from backend.shared.constants.enums.root_cause import RootCauseStatus


class RootCauseApplicationService:
    """
    Root Cause Application Service

    Ownership:
    Owned by the Root Cause Service.

    Operational Purpose:
    The only layer allowed to coordinate the Root Cause Analysis workflow:
    load the persisted Incident, map it to the domain representation the
    (frozen) Rule Engine expects, execute the engine, map its candidate
    back to a persistable row, and save it.

    Architectural Boundaries:
    - Never touches ORM objects across the Rule Engine boundary in either
      direction — `IncidentMapper` and `RootCauseMapper` are the only
      translation points.
    - Enforces the one-incident-to-one-root-cause business rule explicitly
      (checked here, backed by a database unique constraint as the final
      safety net) — this is business policy, not persistence, so it does
      not belong in the repository.
    """

    def __init__(
        self,
        incident_read_repository: IncidentReadRepository,
        root_cause_repository: RootCauseRepository,
        engine: RootCauseEngine,
    ) -> None:
        self.incident_read_repository = incident_read_repository
        self.root_cause_repository = root_cause_repository
        self.engine = engine

    async def create_root_cause(self, incident_id: uuid.UUID) -> RootCause:
        persisted_incident = await self.incident_read_repository.get_by_id(incident_id)
        if persisted_incident is None:
            raise IncidentNotFoundError(incident_id)

        existing = await self.root_cause_repository.get_by_incident(incident_id)
        if existing is not None:
            raise RootCauseAlreadyExistsError(incident_id)

        domain_incident = IncidentMapper.to_domain(persisted_incident)
        candidate = self.engine.analyze(domain_incident)
        root_cause = RootCauseMapper.to_orm(incident_id, candidate)
        return await self.root_cause_repository.save(root_cause)

    async def get_root_cause(self, root_cause_id: uuid.UUID) -> Optional[RootCause]:
        return await self.root_cause_repository.get(root_cause_id)

    async def get_root_cause_by_incident(self, incident_id: uuid.UUID) -> Optional[RootCause]:
        return await self.root_cause_repository.get_by_incident(incident_id)

    async def list_root_causes(self) -> Sequence[RootCause]:
        return await self.root_cause_repository.list()

    async def confirm_root_cause(self, root_cause_id: uuid.UUID) -> RootCause:
        """Confirms a RootCause. Idempotent if already CONFIRMED; 409 if REJECTED."""
        return await self._transition(root_cause_id, RootCauseStatus.CONFIRMED)

    async def reject_root_cause(self, root_cause_id: uuid.UUID) -> RootCause:
        """Rejects a RootCause. Idempotent if already REJECTED; 409 if CONFIRMED."""
        return await self._transition(root_cause_id, RootCauseStatus.REJECTED)

    async def refresh_root_cause(self, root_cause_id: uuid.UUID) -> RootCause:
        """
        Re-runs the (frozen) Rule Engine for a RootCause's Incident and
        updates its analysis fields in place. Only allowed while IDENTIFIED
        — CONFIRMED/REJECTED are final human decisions this step must never
        silently overwrite. If the engine now finds no matching rule, the
        RootCause is persisted as UNKNOWN with status left as IDENTIFIED —
        no new lifecycle state is introduced for this case.
        """
        root_cause = await self.root_cause_repository.get(root_cause_id)
        if root_cause is None:
            raise RootCauseNotFoundError(root_cause_id)
        LifecycleValidator.validate_refresh(root_cause.status)

        persisted_incident = await self.incident_read_repository.get_by_id(root_cause.incident_id)
        if persisted_incident is None:
            raise IncidentNotFoundError(root_cause.incident_id)

        domain_incident = IncidentMapper.to_domain(persisted_incident)
        candidate = self.engine.analyze(domain_incident)
        RootCauseMapper.apply(root_cause, candidate)
        root_cause.updated_at = datetime.now(timezone.utc)
        return await self.root_cause_repository.update(root_cause)

    async def _transition(self, root_cause_id: uuid.UUID, target_status: RootCauseStatus) -> RootCause:
        root_cause = await self.root_cause_repository.get(root_cause_id)
        if root_cause is None:
            raise RootCauseNotFoundError(root_cause_id)

        LifecycleValidator.validate_transition(root_cause.status, target_status)
        root_cause.status = target_status
        root_cause.updated_at = datetime.now(timezone.utc)
        return await self.root_cause_repository.update(root_cause)
