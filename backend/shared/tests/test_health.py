"""
Tests for backend/shared/observability/health.py (Phase 11 Batch 1) --
the additive GET /health/ready readiness endpoint. Reuses the existing,
already-tested `check_database_connection()` primitive rather than
duplicating its logic; these tests confirm the readiness *response shape*
and status-code mapping, mocking only the one existing primitive's
outcome (not inventing a second connectivity check).
"""

from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.shared.observability.health import SERVICE_READINESS, mount_readiness


def _build_app(service_name: str = "test_service") -> FastAPI:
    app = FastAPI()
    mount_readiness(app, service_name=service_name)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "test_service"}

    return app


def test_readiness_returns_200_when_the_database_is_reachable():
    app = _build_app()
    client = TestClient(app)

    with patch("backend.shared.observability.health.check_database_connection", new=AsyncMock(return_value=True)):
        response = client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"] == {"database": "ok"}


def test_readiness_returns_503_when_the_database_is_unreachable():
    app = _build_app()
    client = TestClient(app)

    with patch("backend.shared.observability.health.check_database_connection", new=AsyncMock(return_value=False)):
        response = client.get("/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"] == {"database": "unavailable"}


def test_liveness_health_endpoint_is_unaffected_by_readiness_addition():
    """/health keeps its existing, unmodified contract -- readiness is additive only."""
    app = _build_app()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "test_service"}


# ---------------------------------------------------------------------------
# Phase 11 closure -- `service_readiness` Prometheus gauge
# ---------------------------------------------------------------------------


def test_readiness_endpoint_sets_the_gauge_to_1_when_healthy():
    app = _build_app(service_name="gauge_test_healthy")
    client = TestClient(app)

    with patch("backend.shared.observability.health.check_database_connection", new=AsyncMock(return_value=True)):
        client.get("/health/ready")

    assert SERVICE_READINESS.labels(service="gauge_test_healthy")._value.get() == 1


def test_readiness_endpoint_sets_the_gauge_to_0_when_unhealthy():
    app = _build_app(service_name="gauge_test_unhealthy")
    client = TestClient(app)

    with patch("backend.shared.observability.health.check_database_connection", new=AsyncMock(return_value=False)):
        client.get("/health/ready")

    assert SERVICE_READINESS.labels(service="gauge_test_unhealthy")._value.get() == 0


def test_readiness_gauge_response_body_is_unchanged_by_the_new_label():
    """service_name labels the Prometheus gauge only -- it must never appear
    in the /health/ready JSON response body itself."""
    app = _build_app(service_name="gauge_test_body")
    client = TestClient(app)

    with patch("backend.shared.observability.health.check_database_connection", new=AsyncMock(return_value=True)):
        response = client.get("/health/ready")

    assert response.json() == {"status": "ready", "checks": {"database": "ok"}}
