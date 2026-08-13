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

from backend.shared.observability.health import mount_readiness


def _build_app() -> FastAPI:
    app = FastAPI()
    mount_readiness(app)

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
