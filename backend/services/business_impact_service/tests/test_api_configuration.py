"""
API tests for GET /api/v1/configuration/business-impact (Step 7.X G-05):
read-only visibility into Business Impact's real, currently-active engine
configuration. No fixtures/mocking required -- the endpoint reads real
module-level constants directly, so these tests assert against the same
constants imported here.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.services.business_impact_service.app.domain.impact_dimension import ImpactDimension
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.main import app
from backend.services.business_impact_service.app.services.scoring import IMPACT_LEVEL_POINTS, SEVERITY_BANDS
from backend.services.business_impact_service.app.services.weighting import DIMENSION_WEIGHTS


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_get_configuration_returns_real_dimension_weights():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/configuration/business-impact")

    assert response.status_code == 200
    body = response.json()
    returned_weights = {item["dimension"]: item["weight"] for item in body["dimension_weights"]}
    expected_weights = {dimension.value: weight for dimension, weight in DIMENSION_WEIGHTS.items()}
    assert returned_weights == expected_weights


@pytest.mark.anyio
async def test_get_configuration_returns_real_impact_level_points():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/configuration/business-impact")

    body = response.json()
    returned_points = {item["level"]: item["points"] for item in body["impact_level_points"]}
    expected_points = {level.value: points for level, points in IMPACT_LEVEL_POINTS.items()}
    assert returned_points == expected_points


@pytest.mark.anyio
async def test_get_configuration_returns_real_severity_bands():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/configuration/business-impact")

    body = response.json()
    returned_bands = [(item["upper_bound_inclusive"], item["level"]) for item in body["severity_bands"]]
    expected_bands = [(upper_bound, level.value) for upper_bound, level in SEVERITY_BANDS]
    assert returned_bands == expected_bands


@pytest.mark.anyio
async def test_get_configuration_dimension_weights_cover_every_dimension():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/configuration/business-impact")

    body = response.json()
    returned_dimensions = {item["dimension"] for item in body["dimension_weights"]}
    assert returned_dimensions == {dimension.value for dimension in ImpactDimension}


@pytest.mark.anyio
async def test_get_configuration_impact_level_points_cover_every_level():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/configuration/business-impact")

    body = response.json()
    returned_levels = {item["level"] for item in body["impact_level_points"]}
    assert returned_levels == {level.value for level in ImpactLevel}


@pytest.mark.anyio
async def test_get_configuration_exposes_no_secrets_or_credentials():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/configuration/business-impact")

    body_text = response.text.lower()
    for forbidden_term in ("password", "secret", "token", "api_key", "apikey", "database_url", "credential", "://"):
        assert forbidden_term not in body_text


@pytest.mark.anyio
async def test_configuration_endpoint_has_no_mutation_route():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        post_response = await client.post("/api/v1/configuration/business-impact", json={})
        put_response = await client.put("/api/v1/configuration/business-impact", json={})
        patch_response = await client.patch("/api/v1/configuration/business-impact", json={})
        delete_response = await client.delete("/api/v1/configuration/business-impact")

    assert post_response.status_code == 405
    assert put_response.status_code == 405
    assert patch_response.status_code == 405
    assert delete_response.status_code == 405


@pytest.mark.anyio
async def test_configuration_response_is_stable_across_repeated_calls():
    """Read-only, non-persisted: two consecutive reads return byte-identical results."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = await client.get("/api/v1/configuration/business-impact")
        second = await client.get("/api/v1/configuration/business-impact")

    assert first.json() == second.json()
