"""
Integration test: IntelligenceContext -> RecommendationEngine (real, frozen
Step 1 rules/consolidator) -> RecommendationRepository.save_many() -> REST
API read-back. Proves every field computed by the real domain pipeline
survives, unchanged, all the way through persistence to the JSON response
-- the full Step 2 workflow end to end, using the real engine rather than
a hand-built Recommendation.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.services.recommendation_service.app.domain.recommendation_engine import RecommendationEngine, default_rules
from backend.services.recommendation_service.app.main import app
from backend.services.recommendation_service.app.presentation.dependencies import get_recommendation_repository
from backend.services.recommendation_service.tests.fakes import FakeRecommendationRepository


@pytest.fixture
def anyio_backend():
    return "asyncio"


DATASET_ID = uuid.uuid4()
DATASET_VERSION_ID = uuid.uuid4()


@pytest.mark.anyio
async def test_full_lifecycle_engine_to_persistence_to_api(
    make_incident, make_business_impact_summary, make_intelligence_context
):
    repository = FakeRecommendationRepository()
    context = make_intelligence_context(
        incident=make_incident(),
        business_impact=make_business_impact_summary(overall_severity="critical"),
    )

    recommendations = RecommendationEngine(rules=default_rules()).generate(context)
    assert len(recommendations) > 0  # a critical-severity context always produces at least Escalate

    generation_id = uuid.uuid4()
    persisted = await repository.save_many(
        recommendations, dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id=context.incident.incident_id, generation_id=generation_id
    )
    assert len(persisted) == len(recommendations)

    app.dependency_overrides[get_recommendation_repository] = lambda: repository
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            detail_response = await client.get(f"/api/v1/recommendations/{persisted[0].recommendation_id}")
    finally:
        app.dependency_overrides.clear()

    assert detail_response.status_code == 200
    body = detail_response.json()
    assert body["recommendation_id"] == str(persisted[0].recommendation_id)
    assert body["incident_id"] == context.incident.incident_id
    assert body["category"] == persisted[0].recommendation.category.value
    assert body["priority"] == persisted[0].recommendation.priority.value
    assert body["score"] == persisted[0].recommendation.score
    assert body["action"] == persisted[0].recommendation.action
    assert body["recommendation_rationale"] == persisted[0].recommendation.rationale
    assert body["priority_rationale"] == persisted[0].recommendation.priority_rationale
    assert len(body["supporting_evidence"]) == len(persisted[0].recommendation.supporting_evidence)


@pytest.mark.anyio
async def test_full_lifecycle_is_reachable_via_list_and_latest_endpoints(
    make_incident, make_business_impact_summary, make_intelligence_context
):
    repository = FakeRecommendationRepository()
    context = make_intelligence_context(
        incident=make_incident(incident_id="INC-LIFECYCLE"),
        business_impact=make_business_impact_summary(overall_severity="critical"),
    )

    recommendations = RecommendationEngine(rules=default_rules()).generate(context)
    generation_id = uuid.uuid4()
    persisted = await repository.save_many(
        recommendations, dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id=context.incident.incident_id, generation_id=generation_id
    )

    app.dependency_overrides[get_recommendation_repository] = lambda: repository
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            list_response = await client.get("/api/v1/incidents/INC-LIFECYCLE/recommendations")
            latest_response = await client.get("/api/v1/incidents/INC-LIFECYCLE/recommendations/latest")
            generation_response = await client.get(f"/api/v1/recommendations/generations/{generation_id}")
    finally:
        app.dependency_overrides.clear()

    persisted_ids = {str(record.recommendation_id) for record in persisted}
    assert {item["recommendation_id"] for item in list_response.json()} == persisted_ids
    assert {item["recommendation_id"] for item in latest_response.json()} == persisted_ids
    assert {item["recommendation_id"] for item in generation_response.json()} == persisted_ids


@pytest.mark.anyio
async def test_zero_recommendation_engine_output_still_persists_the_generation(
    make_incident, make_business_impact_summary, make_root_cause, make_intelligence_context
):
    """A genuinely zero-recommendation engine run still records that the execution happened."""
    repository = FakeRecommendationRepository()
    from backend.shared.constants.enums.anomaly import AnomalySeverity

    context = make_intelligence_context(
        incident=make_incident(incident_id="INC-ZERO", severity=AnomalySeverity.NORMAL),
        business_impact=make_business_impact_summary(overall_severity="medium"),
        root_cause=make_root_cause(confidence_score=90),
    )

    recommendations = RecommendationEngine(rules=default_rules()).generate(context)
    assert recommendations == ()

    generation_id = uuid.uuid4()
    persisted = await repository.save_many(recommendations, dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-ZERO", generation_id=generation_id)
    assert persisted == []

    app.dependency_overrides[get_recommendation_repository] = lambda: repository
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/incidents/INC-ZERO/recommendations/latest")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_multiple_generations_for_the_same_incident_are_independently_addressable(
    make_incident, make_business_impact_summary, make_intelligence_context
):
    """Two engine executions for one incident produce two independently-retrievable generations, latest wins for /latest."""
    repository = FakeRecommendationRepository()
    incident = make_incident(incident_id="INC-MULTI")

    first_context = make_intelligence_context(incident=incident, business_impact=make_business_impact_summary(overall_severity="low"))
    second_context = make_intelligence_context(incident=incident, business_impact=make_business_impact_summary(overall_severity="critical"))

    first_recommendations = RecommendationEngine(rules=default_rules()).generate(first_context)
    first_generation = uuid.uuid4()
    await repository.save_many(first_recommendations, dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-MULTI", generation_id=first_generation)

    second_recommendations = RecommendationEngine(rules=default_rules()).generate(second_context)
    second_generation = uuid.uuid4()
    second_persisted = await repository.save_many(second_recommendations, dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-MULTI", generation_id=second_generation)

    app.dependency_overrides[get_recommendation_repository] = lambda: repository
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            all_response = await client.get("/api/v1/incidents/INC-MULTI/recommendations")
            latest_response = await client.get("/api/v1/incidents/INC-MULTI/recommendations/latest")
    finally:
        app.dependency_overrides.clear()

    assert len(all_response.json()) == len(first_recommendations) + len(second_recommendations)
    assert {item["recommendation_id"] for item in latest_response.json()} == {
        str(record.recommendation_id) for record in second_persisted
    }
