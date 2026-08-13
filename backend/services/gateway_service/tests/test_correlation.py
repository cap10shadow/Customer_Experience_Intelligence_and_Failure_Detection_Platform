import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.shared.observability.correlation import CORRELATION_HEADER, CorrelationIdMiddleware


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/ping")
    def ping():
        return {"pong": True}

    return app


def test_generates_a_request_id_when_caller_supplies_none():
    client = TestClient(_build_app())

    response = client.get("/ping")

    request_id = response.headers[CORRELATION_HEADER]
    assert request_id
    # Confirms it's a real generated UUID, not an empty/placeholder value.
    uuid.UUID(request_id)


def test_echoes_back_a_caller_supplied_request_id_unchanged():
    client = TestClient(_build_app())

    response = client.get("/ping", headers={CORRELATION_HEADER: "caller-supplied-id-123"})

    assert response.headers[CORRELATION_HEADER] == "caller-supplied-id-123"


def test_two_requests_without_a_supplied_id_get_different_ids():
    client = TestClient(_build_app())

    first = client.get("/ping").headers[CORRELATION_HEADER]
    second = client.get("/ping").headers[CORRELATION_HEADER]

    assert first != second
