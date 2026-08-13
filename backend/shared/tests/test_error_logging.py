"""
Tests for backend/shared/observability/error_logging.py (Phase 11 Batch 3)
-- the additive unhandled-exception logging handler mounted on the 8
non-Gateway services. Verifies visibility (a genuine unhandled exception
is logged) without changing the existing default response contract these
services already had before this handler existed.
"""

import io
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.shared.logging.logger import get_logger
from backend.shared.observability.error_logging import mount_unhandled_exception_logging


def _build_app() -> FastAPI:
    app = FastAPI()
    mount_unhandled_exception_logging(app)

    @app.get("/boom")
    def boom():
        raise RuntimeError("SELECT * FROM secrets WHERE password = 'hunter2'")

    @app.get("/not-found-item/{item_id}")
    def not_found(item_id: str):
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="item not found")

    return app


def test_unhandled_exception_still_returns_the_original_default_500_response():
    """The response contract these 8 services already had (Starlette's own
    default 500) must not change -- this handler only adds log visibility."""
    client = TestClient(_build_app(), raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_unhandled_exception_is_logged_as_an_error():
    """The exception's own type/traceback (via `exc_info`) is expected in the
    *log* -- operators need it to debug -- the safety boundary this batch
    enforces is the HTTP *response* (asserted separately), which stays
    generic (`test_unhandled_exception_still_returns_the_original_default_500_response`)."""
    client = TestClient(_build_app(), raise_server_exceptions=False)

    logger = get_logger("backend.shared.observability.error_logging")
    stream = io.StringIO()
    handler = logger.handlers[0]
    original_stream = handler.stream
    handler.stream = stream
    try:
        response = client.get("/boom")
    finally:
        handler.stream = original_stream

    assert response.status_code == 500
    lines = [line for line in stream.getvalue().splitlines() if line.strip()]
    assert lines, "expected the unhandled exception to be logged"
    payload = json.loads(lines[0])
    assert payload["level"] == "ERROR"
    assert "RuntimeError" in payload["exception"]


def test_http_exception_is_not_intercepted_by_the_generic_handler():
    """A registered HTTPException (a service's own expected 4xx) must keep
    its normal FastAPI-handled response, not fall through to the generic
    unhandled-exception handler."""
    client = TestClient(_build_app())

    response = client.get("/not-found-item/abc")

    assert response.status_code == 404
    assert response.json() == {"detail": "item not found"}
