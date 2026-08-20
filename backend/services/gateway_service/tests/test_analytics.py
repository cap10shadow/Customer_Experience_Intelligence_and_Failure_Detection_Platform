import uuid

import httpx
import pytest

from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.main import app

DATASET_ID = str(uuid.uuid4())


def _trends_summary(period="Last 30 Days"):
    return {
        "period": period,
        "complaint_volume": [
            {"date": "2026-08-06", "count": 10},
            {"date": "2026-08-07", "count": 15},
            {"date": "2026-08-08", "count": 20},
        ],
        "categories": [
            {"category": "billing", "count": 18},
            {"category": "shipping", "count": 9},
        ],
        "regions": [
            {"region": "EMEA", "count": 12},
            {"region": "unknown", "count": 3},
        ],
        "sentiment": [
            {"date": "2026-08-07", "average_score": -0.5, "label_counts": {"negative": 8, "neutral": 2}},
            {"date": "2026-08-08", "average_score": 0.2, "label_counts": {"positive": 5, "neutral": 3}},
        ],
        "urgency": [
            {"urgency": "high", "count": 7},
            {"urgency": "low", "count": 4},
        ],
    }


def _make_handler(*, status=200, body=None):
    async def handler(request: httpx.Request) -> httpx.Response:
        if status != 200:
            return httpx.Response(status)
        return httpx.Response(200, json=body if body is not None else _trends_summary())

    return handler


def _client_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def override_http_client():
    def _apply(client: httpx.AsyncClient):
        app.dependency_overrides[get_http_client] = lambda: client

    yield _apply
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_analytics_trends_returns_real_backend_fields(override_http_client):
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/analytics/trends", params={"datasetId": DATASET_ID})

    assert response.status_code == 200
    body = response.json()

    assert body["period"] == "Last 30 Days"
    assert body["volumeTrend"] == [
        {"date": "2026-08-06", "count": 10},
        {"date": "2026-08-07", "count": 15},
        {"date": "2026-08-08", "count": 20},
    ]
    assert body["categoryTrend"] == [
        {"category": "billing", "count": 18},
        {"category": "shipping", "count": 9},
    ]
    assert body["regionTrend"] == [
        {"region": "EMEA", "count": 12},
        {"region": "unknown", "count": 3},
    ]
    assert body["sentimentTrend"] == [
        {"date": "2026-08-07", "averageScore": -0.5, "labelCounts": {"negative": 8, "neutral": 2}},
        {"date": "2026-08-08", "averageScore": 0.2, "labelCounts": {"positive": 5, "neutral": 3}},
    ]
    assert body["urgencyTrend"] == [
        {"urgency": "high", "count": 7},
        {"urgency": "low", "count": 4},
    ]
    assert body["warnings"] == []


@pytest.mark.anyio
async def test_analytics_response_never_fabricates_unsupported_sections(override_http_client):
    """Pattern Discovery/Organizational Insights/Strategic Opportunities/Recommendation Effectiveness have no backend capability -- none may appear on the Gateway DTO."""
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/analytics/trends", params={"datasetId": DATASET_ID})

    body = response.json()
    forbidden_keys = {
        "patterns",
        "patternDiscovery",
        "organizationalInsights",
        "strategicOpportunities",
        "recommendationEffectiveness",
        "executiveOverview",
        "insights",
        "opportunities",
    }
    assert forbidden_keys.isdisjoint(body.keys())


@pytest.mark.anyio
async def test_default_period_is_last_30_days(override_http_client):
    client = _client_for(_make_handler(body=_trends_summary(period="Last 30 Days")))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/analytics/trends", params={"datasetId": DATASET_ID})

    assert response.status_code == 200
    assert response.json()["period"] == "Last 30 Days"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "period,expected_days",
    [("last-30-days", 30), ("last-quarter", 90), ("last-12-months", 365)],
)
async def test_period_maps_to_the_correct_days_query_param(override_http_client, period, expected_days):
    seen_days = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_days["days"] = request.url.params.get("days")
        return httpx.Response(200, json=_trends_summary())

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/analytics/trends", params={"period": period, "datasetId": DATASET_ID})

    assert response.status_code == 200
    assert seen_days["days"] == str(expected_days)


@pytest.mark.anyio
async def test_unsupported_period_is_rejected_not_silently_substituted(override_http_client):
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/analytics/trends", params={"period": "last-7-days", "datasetId": DATASET_ID})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.anyio
async def test_empty_trend_arrays_are_preserved_not_padded(override_http_client):
    client = _client_for(
        _make_handler(
            body={
                "period": "Last 30 Days",
                "complaint_volume": [],
                "categories": [],
                "regions": [],
                "sentiment": [],
                "urgency": [],
            }
        )
    )
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/analytics/trends", params={"datasetId": DATASET_ID})

    assert response.status_code == 200
    body = response.json()
    assert body["volumeTrend"] == []
    assert body["categoryTrend"] == []
    assert body["regionTrend"] == []
    assert body["sentimentTrend"] == []
    assert body["urgencyTrend"] == []


@pytest.mark.anyio
async def test_two_datasets_never_cross_contaminate_analytics_trends(override_http_client):
    """
    Cross-dataset isolation regression (AD-12): the real anomaly_service
    route is dataset_id-scoped in its own SQL WHERE clause (verified
    directly against a real Postgres during this pass -- Dataset A/B
    manual walkthrough). This test proves the Gateway half of that
    contract: `datasetId` is forwarded to the downstream call verbatim
    for whichever dataset the request actually named, and two requests
    for two different datasets never receive each other's trend data --
    not because of caching (there is none here) but because the Gateway
    must never substitute, memoize across requests, or drop the
    per-request dataset scope.
    """
    dataset_a = str(uuid.uuid4())
    dataset_b = str(uuid.uuid4())
    seen_dataset_ids: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requested_dataset_id = request.url.params["dataset_id"]
        seen_dataset_ids.append(requested_dataset_id)
        if requested_dataset_id == dataset_a:
            return httpx.Response(200, json=_trends_summary(period="Dataset A period"))
        if requested_dataset_id == dataset_b:
            return httpx.Response(200, json={**_trends_summary(period="Dataset B period"), "categories": [{"category": "technical_issue", "count": 99}]})
        raise AssertionError(f"Unexpected dataset_id forwarded downstream: {requested_dataset_id}")

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response_a = await test_client.get("/api/v1/analytics/trends", params={"datasetId": dataset_a})
        response_b = await test_client.get("/api/v1/analytics/trends", params={"datasetId": dataset_b})

    assert seen_dataset_ids == [dataset_a, dataset_b]
    assert response_a.json()["period"] == "Dataset A period"
    assert response_b.json()["period"] == "Dataset B period"
    assert response_a.json()["categoryTrend"] != response_b.json()["categoryTrend"]
    assert {"category": "technical_issue", "count": 99} not in response_a.json()["categoryTrend"]


@pytest.mark.anyio
async def test_downstream_service_failure_fails_the_request(override_http_client):
    client = _client_for(_make_handler(status=500))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/analytics/trends", params={"datasetId": DATASET_ID})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "DOWNSTREAM_SERVICE_FAILURE"


@pytest.mark.anyio
async def test_downstream_unavailable_maps_to_503(override_http_client):
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/analytics/trends", params={"datasetId": DATASET_ID})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DOWNSTREAM_SERVICE_UNAVAILABLE"


@pytest.mark.anyio
async def test_downstream_timeout_maps_to_504(override_http_client):
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/analytics/trends", params={"datasetId": DATASET_ID})

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "DOWNSTREAM_TIMEOUT"


@pytest.mark.anyio
async def test_no_direct_write_route_exists(override_http_client):
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        for method in ("post", "put", "patch", "delete"):
            response = await test_client.request(method, "/api/v1/analytics/trends")
            assert response.status_code == 405
