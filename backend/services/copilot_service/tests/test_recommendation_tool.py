import httpx
import pytest

from backend.services.copilot_service.app.schemas.tools import RecommendationToolInput
from backend.services.copilot_service.app.services import recommendation_tool

RECOMMENDATION_ID = "11111111-1111-1111-1111-111111111111"
INCIDENT_ID = "incident-42"


def _detail_payload(**overrides):
    payload = {
        "recommendation_id": RECOMMENDATION_ID,
        "incident_id": INCIDENT_ID,
        "generation_id": "22222222-2222-2222-2222-222222222222",
        "category": "escalate",
        "priority": "high",
        "score": 88,
        "action": "Escalate to payments team",
        "recommendation_rationale": "The timing aligns with a recent payment gateway change.",
        "priority_rationale": "High business impact warrants immediate attention.",
        "supporting_evidence": [],
        "created_at": "2026-08-08T01:05:00Z",
        "decision": None,
        "decision_note": None,
        "decided_at": None,
    }
    payload.update(overrides)
    return payload


def _client_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_lookup_by_recommendation_id_returns_real_fields():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/recommendations/{RECOMMENDATION_ID}"
        return httpx.Response(200, json=_detail_payload())

    client = _client_for(handler)
    result = await recommendation_tool.run(client, RecommendationToolInput(recommendation_id=RECOMMENDATION_ID))

    assert result.found is True
    assert len(result.recommendations) == 1
    detail = result.recommendations[0]
    assert detail.recommendation_id == RECOMMENDATION_ID
    assert detail.recommendation_rationale == "The timing aligns with a recent payment gateway change."
    assert detail.created_at == "2026-08-08T01:05:00Z"


@pytest.mark.anyio
async def test_lookup_by_recommendation_id_produces_a_real_evidence_reference():
    client = _client_for(lambda request: httpx.Response(200, json=_detail_payload()))
    result = await recommendation_tool.run(client, RecommendationToolInput(recommendation_id=RECOMMENDATION_ID))

    assert len(result.evidence_references) == 1
    evidence = result.evidence_references[0]
    assert evidence.source_id == RECOMMENDATION_ID
    assert evidence.source_type == "recommendation"
    assert evidence.timestamp == "2026-08-08T01:05:00Z"


@pytest.mark.anyio
async def test_missing_recommendation_is_a_legitimate_absence_not_an_error():
    client = _client_for(lambda request: httpx.Response(404))
    result = await recommendation_tool.run(client, RecommendationToolInput(recommendation_id=RECOMMENDATION_ID))

    assert result.found is False
    assert result.error is None


@pytest.mark.anyio
async def test_downstream_failure_is_a_structured_error_not_a_fabricated_result():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = _client_for(handler)
    result = await recommendation_tool.run(client, RecommendationToolInput(recommendation_id=RECOMMENDATION_ID))

    assert result.found is False
    assert result.error is not None
    assert result.recommendations == []


@pytest.mark.anyio
async def test_lookup_by_incident_id_calls_the_latest_endpoint():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/incidents/{INCIDENT_ID}/recommendations/latest"
        return httpx.Response(200, json=[_detail_payload()])

    client = _client_for(handler)
    result = await recommendation_tool.run(client, RecommendationToolInput(incident_id=INCIDENT_ID))

    assert result.found is True
    assert result.recommendations[0].incident_id == INCIDENT_ID


@pytest.mark.anyio
async def test_statistics_are_requested_only_when_explicitly_asked():
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/api/v1/recommendations/statistics":
            return httpx.Response(
                200,
                json={"total_count": 12, "category_counts": {"escalate": 5}, "priority_counts": {"high": 3}, "average_score": 71.5},
            )
        return httpx.Response(200, json=[])

    client = _client_for(handler)
    result = await recommendation_tool.run(client, RecommendationToolInput(include_statistics=True))

    assert "/api/v1/recommendations/statistics" in calls
    assert result.statistics is not None
    assert result.statistics.total_count == 12
    assert result.statistics.average_score == 71.5


@pytest.mark.anyio
async def test_statistics_endpoint_is_never_called_when_not_requested():
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json=[])

    client = _client_for(handler)
    await recommendation_tool.run(client, RecommendationToolInput())

    assert "/api/v1/recommendations/statistics" not in calls
