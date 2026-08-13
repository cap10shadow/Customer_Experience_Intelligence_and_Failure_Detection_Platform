"""
Tests for backend/shared/observability/correlation.py (Phase 11 Batch 1,
OBS-001) -- the shared, cross-service correlation-ID primitive promoted
from gateway_service's former private core/correlation.py. Basic
middleware echo/generate behavior is already covered by
gateway_service/tests/test_correlation.py (now importing from this same
shared module); this file covers the additional surface Batch 1 adds:
the contextvar accessor and outbound-header helper.
"""

import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.shared.observability.correlation import (
    CORRELATION_HEADER,
    CorrelationIdMiddleware,
    correlation_headers,
    get_current_request_id,
)


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/ping")
    async def ping():
        return {"seen_by_get_current_request_id": get_current_request_id()}

    return app


def test_get_current_request_id_returns_none_outside_any_request():
    assert get_current_request_id() is None


def test_get_current_request_id_reflects_the_active_requests_id():
    client = TestClient(_build_app())

    response = client.get("/ping", headers={CORRELATION_HEADER: "ctx-test-id"})

    assert response.json()["seen_by_get_current_request_id"] == "ctx-test-id"


def test_get_current_request_id_reverts_to_none_after_the_request_completes():
    client = TestClient(_build_app())
    client.get("/ping", headers={CORRELATION_HEADER: "ctx-test-id"})

    assert get_current_request_id() is None


def test_correlation_headers_is_empty_outside_any_request():
    assert correlation_headers() == {}


def test_correlation_headers_carries_the_active_requests_id_during_a_request():
    captured = {}

    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/ping")
    async def ping():
        captured["headers"] = correlation_headers()
        return {"ok": True}

    client = TestClient(app)
    client.get("/ping", headers={CORRELATION_HEADER: "outbound-test-id"})

    assert captured["headers"] == {CORRELATION_HEADER: "outbound-test-id"}


def test_correlation_headers_uses_a_generated_id_when_the_caller_supplied_none():
    captured = {}

    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/ping")
    async def ping():
        captured["headers"] = correlation_headers()
        return {"ok": True}

    client = TestClient(app)
    client.get("/ping")

    generated_id = captured["headers"][CORRELATION_HEADER]
    uuid.UUID(generated_id)  # confirms it's a real generated UUID, not a placeholder
