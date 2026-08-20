"""
Unit tests for RecommendationOrchestrator: invokes the real (frozen,
unmodified) RecommendationEngine and coordinates persistence through
FakeRecommendationRepository -- no database, no lifecycle, no messaging.
"""

import uuid

import pytest

from backend.services.recommendation_service.app.application.orchestration.recommendation_orchestrator import (
    RecommendationOrchestrator,
)
from backend.services.recommendation_service.app.domain.recommendation_engine import RecommendationEngine, default_rules
from backend.services.recommendation_service.app.domain.recommendation_record import RecommendationRecord
from backend.services.recommendation_service.tests.fakes import FakeRecommendationRepository


@pytest.fixture
def anyio_backend():
    return "asyncio"


DATASET_ID = uuid.uuid4()
DATASET_VERSION_ID = uuid.uuid4()


def _orchestrator(repository=None) -> RecommendationOrchestrator:
    return RecommendationOrchestrator(
        engine=RecommendationEngine(rules=default_rules()),
        repository=repository if repository is not None else FakeRecommendationRepository(),
    )


@pytest.mark.anyio
async def test_invokes_the_real_recommendation_engine(make_incident, make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(
        incident=make_incident(), business_impact=make_business_impact_summary(overall_severity="critical")
    )

    result = await _orchestrator().execute(context, generation_id=uuid.uuid4(), dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID)

    assert len(result) > 0
    assert all(isinstance(record, RecommendationRecord) for record in result)


@pytest.mark.anyio
async def test_persists_recommendation_generation_and_recommendations(
    make_incident, make_business_impact_summary, make_intelligence_context
):
    repository = FakeRecommendationRepository()
    context = make_intelligence_context(
        incident=make_incident(incident_id="INC-ORCH"), business_impact=make_business_impact_summary(overall_severity="critical")
    )
    generation_id = uuid.uuid4()

    result = await _orchestrator(repository).execute(context, generation_id=generation_id, dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID)

    assert len(repository.by_id) == len(result)
    assert all(record.generation_id == generation_id for record in result)
    assert repository.generations_by_incident["INC-ORCH"][0][0] == generation_id


@pytest.mark.anyio
async def test_generation_id_propagates_to_every_persisted_recommendation(
    make_incident, make_business_impact_summary, make_intelligence_context
):
    context = make_intelligence_context(
        incident=make_incident(), business_impact=make_business_impact_summary(overall_severity="critical")
    )
    generation_id = uuid.uuid4()

    result = await _orchestrator().execute(context, generation_id=generation_id, dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID)

    assert len(result) > 1  # a critical scenario fires multiple rules
    assert all(record.generation_id == generation_id for record in result)


@pytest.mark.anyio
async def test_event_id_forwarded_to_the_repository(make_incident, make_business_impact_summary, make_intelligence_context):
    repository = FakeRecommendationRepository()
    context = make_intelligence_context(
        incident=make_incident(), business_impact=make_business_impact_summary(overall_severity="critical")
    )
    event_id = uuid.uuid4()

    await _orchestrator(repository).execute(context, generation_id=uuid.uuid4(), dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, event_id=event_id)

    assert await repository.get_generation_by_event_id(event_id) is not None


@pytest.mark.anyio
async def test_zero_recommendations_still_persists_the_generation(
    make_incident, make_business_impact_summary, make_root_cause, make_intelligence_context
):
    from backend.shared.constants.enums.anomaly import AnomalySeverity

    repository = FakeRecommendationRepository()
    context = make_intelligence_context(
        incident=make_incident(incident_id="INC-ZERO", severity=AnomalySeverity.NORMAL),
        business_impact=make_business_impact_summary(overall_severity="medium"),
        root_cause=make_root_cause(confidence_score=90),
    )
    generation_id = uuid.uuid4()

    result = await _orchestrator(repository).execute(context, generation_id=generation_id, dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID)

    assert result == ()
    assert repository.generations_by_incident["INC-ZERO"][0][0] == generation_id


@pytest.mark.anyio
async def test_result_is_an_immutable_tuple(make_incident, make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(
        incident=make_incident(), business_impact=make_business_impact_summary(overall_severity="critical")
    )

    result = await _orchestrator().execute(context, generation_id=uuid.uuid4(), dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID)

    assert isinstance(result, tuple)


@pytest.mark.anyio
async def test_never_creates_its_own_generation_id(make_incident, make_business_impact_summary, make_intelligence_context):
    """The orchestrator must use exactly the generation_id it is given -- it never mints its own."""
    context = make_intelligence_context(
        incident=make_incident(), business_impact=make_business_impact_summary(overall_severity="critical")
    )
    supplied_generation_id = uuid.uuid4()

    result = await _orchestrator().execute(context, generation_id=supplied_generation_id, dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID)

    assert all(record.generation_id == supplied_generation_id for record in result)


@pytest.mark.anyio
async def test_is_deterministic_across_repeated_calls(make_incident, make_business_impact_summary, make_intelligence_context):
    context = make_intelligence_context(
        incident=make_incident(), business_impact=make_business_impact_summary(overall_severity="critical")
    )
    orchestrator = _orchestrator()

    first = await orchestrator.execute(context, generation_id=uuid.uuid4(), dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID)
    second = await orchestrator.execute(context, generation_id=uuid.uuid4(), dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID)

    assert [r.recommendation for r in first] == [r.recommendation for r in second]
