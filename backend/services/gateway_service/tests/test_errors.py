import io
import json

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel

from backend.shared.logging.logger import get_logger
from backend.shared.observability.correlation import CorrelationIdMiddleware
from backend.services.gateway_service.app.core.errors import (
    ConflictError,
    DownstreamServiceError,
    DownstreamTimeoutError,
    DownstreamUnavailableError,
    GatewayError,
    GatewayValidationError,
    ResourceNotFoundError,
    gateway_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)


@pytest.mark.parametrize(
    ("error_cls", "expected_status", "expected_code"),
    [
        (GatewayValidationError, 400, "VALIDATION_ERROR"),
        (ResourceNotFoundError, 404, "RESOURCE_NOT_FOUND"),
        (ConflictError, 409, "CONFLICT"),
        (DownstreamServiceError, 502, "DOWNSTREAM_SERVICE_FAILURE"),
        (DownstreamUnavailableError, 503, "DOWNSTREAM_SERVICE_UNAVAILABLE"),
        (DownstreamTimeoutError, 504, "DOWNSTREAM_TIMEOUT"),
    ],
)
def test_gateway_error_subclasses_carry_the_frozen_status_and_code(error_cls, expected_status, expected_code):
    assert error_cls.status_code == expected_status
    assert error_cls.code == expected_code


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)
    app.add_exception_handler(GatewayError, gateway_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    class Body(BaseModel):
        required_field: str

    @app.get("/not-found")
    def raise_not_found():
        raise ResourceNotFoundError("Incident was not found.", details={"incidentId": "abc-123"})

    @app.post("/validated")
    def validated(body: Body):
        return {"ok": True}

    @app.get("/boom")
    def raise_unhandled():
        raise RuntimeError("SELECT * FROM secrets WHERE password = 'hunter2'")

    return app


@pytest.fixture
def client():
    app = _build_test_app()
    return TestClient(app, raise_server_exceptions=False)


def test_gateway_error_returns_standardized_envelope(client):
    response = client.get("/not-found")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert body["error"]["message"] == "Incident was not found."
    assert body["error"]["details"] == {"incidentId": "abc-123"}
    assert body["error"]["requestId"]


def test_gateway_error_request_id_matches_correlation_header(client):
    response = client.get("/not-found", headers={"X-Request-ID": "test-request-id"})

    assert response.headers["X-Request-ID"] == "test-request-id"
    assert response.json()["error"]["requestId"] == "test-request-id"


def test_request_validation_error_returns_422_envelope(client):
    response = client.post("/validated", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["requestId"]


def test_unhandled_exception_never_leaks_exception_details(client):
    response = client.get("/boom")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["message"] == "An unexpected error occurred."
    assert "secrets" not in str(body)
    assert "hunter2" not in str(body)
    assert "RuntimeError" not in str(body)


# ---------------------------------------------------------------------------
# Batch 3 -- error logging coverage / severity classification
#
# Uses the same real-formatter, captured-stream approach as
# backend/shared/tests/test_logger.py (swapping the logger's own stdout
# handler's stream) rather than pytest's `caplog`, since `get_logger()`
# deliberately sets `propagate = False` (Batch 1) so nothing double-logs
# through Docker/uvicorn's root handlers -- `caplog`'s default handler
# lives on the root logger, so it never observes these records.
# ---------------------------------------------------------------------------


def _capture_log_lines(logger_name: str, make_request) -> list[dict]:
    logger = get_logger(logger_name)
    stream = io.StringIO()
    handler = logger.handlers[0]
    original_stream = handler.stream
    handler.stream = stream
    try:
        response = make_request()
    finally:
        handler.stream = original_stream
    lines = [line for line in stream.getvalue().splitlines() if line.strip()]
    return response, [json.loads(line) for line in lines]


def test_expected_client_error_is_logged_but_not_at_error_severity(client):
    """A genuine 404 is expected, client-facing behavior -- it must be visible
    in logs (Batch 3 error-logging coverage) but never as an ERROR-level
    application failure (§6 of the batch instructions)."""
    response, payloads = _capture_log_lines(
        "backend.services.gateway_service.app.core.errors", lambda: client.get("/not-found")
    )

    assert response.status_code == 404
    assert payloads, "expected GatewayError to be logged"
    assert all(p["level"] != "ERROR" for p in payloads)
    assert payloads[0]["status_code"] == 404
    assert payloads[0]["error_code"] == "RESOURCE_NOT_FOUND"


def test_downstream_server_side_error_is_logged_at_error_severity(client):
    """A 5xx-mapped GatewayError (downstream failure) is a genuine operational
    failure and must be logged at ERROR, per §6/§3.8 of the frozen architecture."""

    @client.app.get("/downstream-boom")
    def _raise_downstream_error():
        raise DownstreamServiceError("recommendation_service returned status 502.")

    response, payloads = _capture_log_lines(
        "backend.services.gateway_service.app.core.errors", lambda: client.get("/downstream-boom")
    )

    assert response.status_code == 502
    assert payloads, "expected DownstreamServiceError to be logged"
    assert payloads[-1]["level"] == "ERROR"
    assert payloads[-1]["status_code"] == 502


def test_gateway_error_log_context_never_carries_raw_details_payload(client):
    """Only bounded, safe context (status/code/route) is attached to the log
    record -- the `details` field (which may carry caller-supplied structured
    data) is never blindly merged into the log's safe_extra."""
    _response, payloads = _capture_log_lines(
        "backend.services.gateway_service.app.core.errors", lambda: client.get("/not-found")
    )

    logged_fields = set(payloads[0].keys()) - {"timestamp", "level", "service", "logger", "message", "request_id"}
    assert logged_fields == {"status_code", "error_code", "route"}
    assert "incidentId" not in json.dumps(payloads[0])
