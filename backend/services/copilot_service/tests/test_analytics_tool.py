import httpx
import pytest

from backend.services.copilot_service.app.schemas.tools import AnalyticsToolInput
from backend.services.copilot_service.app.services import analytics_tool as tool


def _summary_payload():
    return {
        "period": "last_30_days",
        "complaint_volume": [{"date": "2026-08-01", "count": 10}],
        "categories": [{"category": "billing", "count": 4}],
        "regions": [{"region": "west", "count": 6}],
        "sentiment": [{"date": "2026-08-01", "average_score": -0.2, "label_counts": {"negative": 3}}],
        "urgency": [{"urgency": "high", "count": 2}],
    }


def _client_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_summary_dimension_calls_the_real_summary_endpoint():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/trends"
        assert request.url.params["days"] == "30"
        assert request.url.params["dataset_id"] == "dataset-1"
        return httpx.Response(200, json=_summary_payload())

    client = _client_for(handler)
    result = await tool.run(client, AnalyticsToolInput(dimension="summary", days=30, dataset_id="dataset-1"))

    assert result.found is True
    assert result.period == "last_30_days"
    assert result.volume[0].count == 10
    assert result.categories[0].category == "billing"


@pytest.mark.anyio
async def test_daily_dimension_calls_the_real_daily_endpoint_only():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/trends/daily"
        return httpx.Response(200, json={"period": "last_7_days", "complaint_volume": [{"date": "2026-08-08", "count": 5}]})

    client = _client_for(handler)
    result = await tool.run(client, AnalyticsToolInput(dimension="daily", days=7, dataset_id="dataset-1"))

    assert result.volume[0].count == 5
    assert result.categories == []


@pytest.mark.anyio
async def test_freshness_note_states_no_computation_timestamp_is_available():
    client = _client_for(lambda request: httpx.Response(200, json=_summary_payload()))
    result = await tool.run(client, AnalyticsToolInput(dataset_id="dataset-1"))

    assert "does not provide a computation timestamp" in result.freshness_note


@pytest.mark.anyio
async def test_days_is_bounded_to_the_real_endpoint_s_1_to_365_range():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["days"] == "365"
        return httpx.Response(200, json=_summary_payload())

    client = _client_for(handler)
    await tool.run(client, AnalyticsToolInput(days=9999, dataset_id="dataset-1"))


@pytest.mark.anyio
async def test_no_dataset_selected_is_reported_without_calling_the_downstream():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("must not call anomaly_service with no dataset_id")

    client = _client_for(handler)
    result = await tool.run(client, AnalyticsToolInput(dimension="summary"))

    assert result.found is False
    assert result.error is not None
    assert "dataset" in result.error.lower()


@pytest.mark.anyio
async def test_unsupported_dimension_is_reported_not_silently_dropped():
    client = _client_for(lambda request: httpx.Response(200, json=_summary_payload()))
    result = await tool.run(client, AnalyticsToolInput(dimension="not_a_real_dimension"))

    assert result.found is False
    assert result.error is not None


@pytest.mark.anyio
async def test_downstream_failure_is_a_structured_error():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    client = _client_for(handler)
    result = await tool.run(client, AnalyticsToolInput(dataset_id="dataset-1"))

    assert result.found is False
    assert result.error is not None
