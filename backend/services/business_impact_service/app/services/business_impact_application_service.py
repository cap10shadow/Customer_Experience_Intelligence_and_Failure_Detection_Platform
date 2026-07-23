import uuid
from typing import Optional, Sequence

from backend.services.business_impact_service.app.domain.business_priority import BusinessPriority
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.mappers.input_mapper import BusinessImpactInputMapper
from backend.services.business_impact_service.app.mappers.output_mapper import BusinessImpactOutputMapper
from backend.services.business_impact_service.app.models.business_impact_assessment import (
    BusinessImpactAssessmentEntity,
)
from backend.services.business_impact_service.app.repositories.business_impact_repository import (
    BusinessImpactRepository,
)
from backend.services.business_impact_service.app.repositories.incident_read_repository import (
    IncidentReadRepository,
)
from backend.services.business_impact_service.app.repositories.root_cause_read_repository import (
    RootCauseReadRepository,
)
from backend.services.business_impact_service.app.services.exceptions import (
    IncidentNotFoundError,
    RootCauseNotFoundError,
)
from backend.services.business_impact_service.app.services.impact_engine import BusinessImpactEngine


class BusinessImpactApplicationService:
    """
    Business Impact Application Service

    Ownership:
    Owned by the Business Impact Service.

    Operational Purpose:
    The only layer allowed to coordinate the Business Impact Analysis
    workflow: load the persisted Incident (with its linked anomalies), load
    the persisted RootCause, map both into the plain input value objects
    the (frozen) Business Impact Engine expects, execute the engine, map
    its assessment back to a persistable row, and save it.

    Architectural Boundaries:
    - Never touches ORM/read-model rows across the Engine boundary in
      either direction -- `BusinessImpactInputMapper` and
      `BusinessImpactOutputMapper` are the only translation points.
    - Contains no business or scoring logic of its own -- purely
      orchestration. The Engine, its rules, weighting, scoring, and
      explanation are frozen (Phase 7 Step 1) and are never reimplemented
      or duplicated here.
    - Assessments are immutable: there is no update method on this service.
    """

    def __init__(
        self,
        incident_read_repository: IncidentReadRepository,
        root_cause_read_repository: RootCauseReadRepository,
        business_impact_repository: BusinessImpactRepository,
        engine: BusinessImpactEngine,
    ) -> None:
        self.incident_read_repository = incident_read_repository
        self.root_cause_read_repository = root_cause_read_repository
        self.business_impact_repository = business_impact_repository
        self.engine = engine

    async def create_assessment(self, incident_id: uuid.UUID) -> BusinessImpactAssessmentEntity:
        persisted_incident = await self.incident_read_repository.get_by_id(incident_id)
        if persisted_incident is None:
            raise IncidentNotFoundError(incident_id)

        persisted_root_cause = await self.root_cause_read_repository.get_by_incident(incident_id)
        if persisted_root_cause is None:
            raise RootCauseNotFoundError(incident_id)

        incident = BusinessImpactInputMapper.to_incident(persisted_incident)
        root_cause_summary = BusinessImpactInputMapper.to_root_cause_summary(persisted_root_cause)
        trend_metrics = BusinessImpactInputMapper.to_trend_metrics(persisted_incident)
        anomaly_metrics = BusinessImpactInputMapper.to_anomaly_metrics(persisted_incident)

        assessment = self.engine.analyze(incident, root_cause_summary, trend_metrics, anomaly_metrics)

        entity = BusinessImpactOutputMapper.to_orm(incident_id, persisted_root_cause.id, assessment)
        return await self.business_impact_repository.save(entity)

    async def get_assessment(self, assessment_id: uuid.UUID) -> Optional[BusinessImpactAssessmentEntity]:
        return await self.business_impact_repository.get(assessment_id)

    async def list_assessments(
        self,
        *,
        severity: Optional[ImpactLevel] = None,
        priority: Optional[BusinessPriority] = None,
        incident_id: Optional[uuid.UUID] = None,
    ) -> Sequence[BusinessImpactAssessmentEntity]:
        return await self.business_impact_repository.list(severity=severity, priority=priority, incident_id=incident_id)
