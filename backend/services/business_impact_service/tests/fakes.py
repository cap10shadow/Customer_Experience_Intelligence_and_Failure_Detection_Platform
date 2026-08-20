"""
Shared, in-memory test support for Phase 7 Step 3 (Lifecycle & Validation).

Not a test module itself (no `test_` prefix -- pytest will not collect it).

No real-database test infrastructure exists anywhere in this repository
(consistent with every other service's test suite: root_cause_service and
anomaly_service also validate exclusively against in-memory Fakes). These
Fakes expose the exact same async contract as the real, SQLAlchemy-backed
repositories (`IncidentReadRepository`, `RootCauseReadRepository`,
`BusinessImpactRepository`), so wiring them into the real
`BusinessImpactInputMapper`, the real `BusinessImpactEngine`, the real
`BusinessImpactOutputMapper`, and the real `BusinessImpactApplicationService`
still validates every architectural boundary except the final SQL execution
itself -- exactly the boundary Root Cause Service's own Step 2/3 test suite
also stops short of.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Sequence

from backend.services.business_impact_service.app.domain.business_priority import BusinessPriority
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.models.business_impact_assessment import (
    BusinessImpactAssessmentEntity,
)
from backend.services.business_impact_service.app.repositories.incident_read_repository import (
    PersistedActiveAnomaly,
    PersistedIncident,
)
from backend.services.business_impact_service.app.repositories.root_cause_read_repository import PersistedRootCause
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType
from backend.shared.constants.enums.business_impact_assessment import BusinessImpactAssessmentStatus
from backend.shared.constants.enums.root_cause import RootCause

DATASET_ID = uuid.uuid4()
DATASET_VERSION_ID = uuid.uuid4()


class FakeIncidentReadRepository:
    """In-memory stand-in for IncidentReadRepository -- same async contract, no database."""

    def __init__(self, incidents_by_id: Dict[uuid.UUID, PersistedIncident]) -> None:
        self._incidents_by_id = incidents_by_id

    async def get_by_id(self, incident_id: uuid.UUID) -> Optional[PersistedIncident]:
        return self._incidents_by_id.get(incident_id)


class FakeRootCauseReadRepository:
    """In-memory stand-in for RootCauseReadRepository -- same async contract, no database."""

    def __init__(self, root_causes_by_incident_id: Dict[uuid.UUID, PersistedRootCause]) -> None:
        self._root_causes_by_incident_id = root_causes_by_incident_id

    async def get_by_incident(self, incident_id: uuid.UUID) -> Optional[PersistedRootCause]:
        return self._root_causes_by_incident_id.get(incident_id)


class FakeBusinessImpactRepository:
    """
    In-memory stand-in for BusinessImpactRepository -- same async contract, no database.

    `save` explicitly assigns `assessment_id`, `status`, `created_at`, and
    `updated_at` because those columns are populated by PostgreSQL itself
    (primary key default, column defaults, server defaults) on a real flush.
    This mirrors the same precedent already established by Root Cause
    Service's own `FakeRootCauseRepository.save`, which manually assigns
    `root_cause.id` for the same reason.
    """

    def __init__(self) -> None:
        self.by_id: Dict[uuid.UUID, BusinessImpactAssessmentEntity] = {}

    async def save(self, entity: BusinessImpactAssessmentEntity) -> BusinessImpactAssessmentEntity:
        entity.assessment_id = uuid.uuid4()
        entity.status = BusinessImpactAssessmentStatus.ACTIVE
        entity.created_at = datetime.now(timezone.utc)
        entity.updated_at = entity.created_at
        self.by_id[entity.assessment_id] = entity
        return entity

    async def get(
        self, assessment_id: uuid.UUID, dataset_id: Optional[uuid.UUID] = None
    ) -> Optional[BusinessImpactAssessmentEntity]:
        entity = self.by_id.get(assessment_id)
        if entity is None or dataset_id is None:
            return entity
        return entity if entity.dataset_id == dataset_id else None

    async def list(
        self,
        *,
        severity: Optional[ImpactLevel] = None,
        priority: Optional[BusinessPriority] = None,
        incident_id: Optional[uuid.UUID] = None,
        dataset_id: Optional[uuid.UUID] = None,
        dataset_version_id: Optional[uuid.UUID] = None,
    ) -> Sequence[BusinessImpactAssessmentEntity]:
        results = list(self.by_id.values())
        if severity is not None:
            results = [r for r in results if r.overall_severity == severity]
        if priority is not None:
            results = [r for r in results if r.business_priority == priority]
        if incident_id is not None:
            results = [r for r in results if r.incident_id == incident_id]
        if dataset_id is not None:
            results = [r for r in results if r.dataset_id == dataset_id]
        if dataset_version_id is not None:
            results = [r for r in results if r.dataset_version_id == dataset_version_id]
        return results


class NoopEventPublisher:
    """
    In-memory stand-in for BusinessImpactEventPublisher -- same async
    `publish(event)` contract, records what it was given rather than
    performing any real HTTP delivery. Used by tests (Part 6) that drive
    `create_assessment` through the real FastAPI app via ASGITransport
    (so no `app.state.http_client` exists, unlike a real lifespan run) but
    don't care about event delivery itself.
    """

    def __init__(self) -> None:
        self.published = []

    async def publish(self, event) -> list:
        self.published.append(event)
        return []


def build_realistic_incident_scenario():
    """
    Builds one realistic, independently hand-computable synthetic Incident +
    RootCause scenario: a critical service-outage incident with a
    complaint-volume spike, a two-region spread, critical urgency, and a
    confirmed sentiment-shift signal.

    Returns a fresh (incident_id, PersistedIncident, PersistedRootCause)
    tuple on every call -- callers that need two independent runs over
    "identical inputs" (e.g. determinism tests) should call this twice
    rather than reuse one instance, so no test can pass merely by aliasing
    the same Python objects.
    """
    incident_id = uuid.uuid4()
    anomalies = (
        PersistedActiveAnomaly(
            id=uuid.uuid4(), type=AnomalyType.COMPLAINT_SPIKE, entity_type="global", entity_value=None,
            baseline_value=200.0, current_value=500.0, percentage_change=150.0,
        ),
        PersistedActiveAnomaly(
            id=uuid.uuid4(), type=AnomalyType.REGIONAL_SPIKE, entity_type="region", entity_value="us-east",
            baseline_value=20.0, current_value=60.0, percentage_change=200.0,
        ),
        PersistedActiveAnomaly(
            id=uuid.uuid4(), type=AnomalyType.REGIONAL_SPIKE, entity_type="region", entity_value="us-west",
            baseline_value=15.0, current_value=45.0, percentage_change=200.0,
        ),
        PersistedActiveAnomaly(
            id=uuid.uuid4(), type=AnomalyType.URGENCY_SPIKE, entity_type="urgency", entity_value="critical",
            baseline_value=5.0, current_value=25.0, percentage_change=400.0,
        ),
        PersistedActiveAnomaly(
            id=uuid.uuid4(), type=AnomalyType.SENTIMENT_SHIFT, entity_type="global", entity_value=None,
            baseline_value=0.2, current_value=-0.6, percentage_change=-400.0,
        ),
    )
    persisted_incident = PersistedIncident(id=incident_id, severity=AnomalySeverity.CRITICAL, anomalies=anomalies)
    persisted_root_cause = PersistedRootCause(
        id=uuid.uuid4(),
        incident_id=incident_id,
        cause=RootCause.SERVICE_OUTAGE,
        confidence_score=90,
        confidence_level="Very High",
    )
    return incident_id, persisted_incident, persisted_root_cause


# Hand-computed expected results for `build_realistic_incident_scenario()`,
# derived independently from the frozen Phase 7 Step 1 engine's documented
# rule logic and Phase 7 Step 2's documented mapper defaults (sla_breach_count
# and negative_sentiment_ratio are always 0 / 0.0 via the real mapper, so SLA
# and Reputation are expected to be NONE regardless of the anomalies present
# -- this is current, documented, correct behavior, not an oversight).
EXPECTED_FINANCIAL = ImpactLevel.CRITICAL
EXPECTED_CUSTOMER = ImpactLevel.CRITICAL
EXPECTED_OPERATIONAL = ImpactLevel.CRITICAL
EXPECTED_SLA = ImpactLevel.NONE
EXPECTED_REPUTATION = ImpactLevel.NONE
EXPECTED_OVERALL_SCORE = 75
EXPECTED_OVERALL_SEVERITY = ImpactLevel.HIGH
EXPECTED_BUSINESS_PRIORITY = BusinessPriority.HIGH
EXPECTED_CONFIDENCE = 60
EXPECTED_AFFECTED_CUSTOMERS = 500
EXPECTED_EXPLANATION = (
    "Overall business impact is high (score: 75, priority: high). "
    "Reasons: financial (critical): Critical-severity incident with a 150% complaint volume increase; "
    "customer (critical): 500 customers affected, escalated due to high/critical urgency signals; "
    "operational (critical): service_outage identified with critical anomaly severity; "
    "sla (none): No SLA breaches reported; "
    "reputation (none): No negative sentiment signal detected."
)
