import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel

from backend.services.gateway_service.app.core.correlation import CorrelationIdMiddleware
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
