import httpx
from fastapi.testclient import TestClient

from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.main import app


def test_health_check_returns_ok_without_touching_any_downstream_service():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "gateway_service"}


def test_lifespan_creates_a_single_shared_http_client_with_the_configured_timeout():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200

        assert isinstance(app.state.http_client, httpx.AsyncClient)
        assert app.state.http_client.timeout.connect == settings.DOWNSTREAM_TIMEOUT_SECONDS


def test_get_http_client_dependency_returns_the_app_state_client():
    with TestClient(app) as client:
        client.get("/health")

        class _FakeRequest:
            def __init__(self, fastapi_app):
                self.app = fastapi_app

        resolved = get_http_client(_FakeRequest(app))

    assert resolved is app.state.http_client


def test_cors_allows_a_configured_frontend_origin():
    allowed_origin = settings.cors_allowed_origins[0]

    with TestClient(app) as client:
        response = client.options(
            "/health",
            headers={
                "Origin": allowed_origin,
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.headers.get("access-control-allow-origin") == allowed_origin


def test_cors_rejects_an_unconfigured_origin():
    with TestClient(app) as client:
        response = client.options(
            "/health",
            headers={
                "Origin": "http://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.headers.get("access-control-allow-origin") != "http://evil.example.com"


def test_response_carries_a_correlation_id_header():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.headers.get("X-Request-ID")
