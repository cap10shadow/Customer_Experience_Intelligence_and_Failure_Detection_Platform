import pytest
from httpx import AsyncClient, ASGITransport

from backend.services.anomaly_service.app.main import app
from backend.services.anomaly_service.app.dependencies.services import get_trend_engine
from backend.services.anomaly_service.app.schemas.trends import (
    CategoryTrendResponse,
    RegionTrendResponse,
    SentimentTrendResponse,
    TrendSummaryResponse,
    UrgencyTrendResponse,
    VolumeTrendResponse,
)


class MockTrendEngine:
    async def get_summary(self, days):
        return TrendSummaryResponse(
            period=f"Last {days} Days",
            complaint_volume=[],
            categories=[],
            regions=[],
            sentiment=[],
            urgency=[],
        )

    async def get_volume_trend(self, days):
        return VolumeTrendResponse(period=f"Last {days} Days", complaint_volume=[])

    async def get_category_trend(self, days):
        return CategoryTrendResponse(period=f"Last {days} Days", categories=[])

    async def get_region_trend(self, days):
        return RegionTrendResponse(period=f"Last {days} Days", regions=[])

    async def get_sentiment_trend(self, days):
        return SentimentTrendResponse(period=f"Last {days} Days", sentiment=[])

    async def get_urgency_trend(self, days):
        return UrgencyTrendResponse(period=f"Last {days} Days", urgency=[])


@pytest.fixture
def override_dependencies():
    app.dependency_overrides[get_trend_engine] = lambda: MockTrendEngine()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "path",
    ["/trends", "/trends/daily", "/trends/categories", "/trends/regions", "/trends/sentiment", "/trends/urgency"],
)
async def test_trend_endpoints_return_200(override_dependencies, path):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/v1{path}")
        assert response.status_code == 200
        assert response.json()["period"] == "Last 30 Days"


@pytest.mark.anyio
async def test_days_query_param_is_honored(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/trends?days=7")
        assert response.status_code == 200
        assert response.json()["period"] == "Last 7 Days"


@pytest.mark.anyio
async def test_days_query_param_rejects_out_of_range(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/trends?days=0")
        assert response.status_code == 422

        response = await client.get("/api/v1/trends?days=366")
        assert response.status_code == 422
