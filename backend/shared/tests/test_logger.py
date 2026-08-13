"""
Tests for backend/shared/logging/logger.py's structured JSON rewrite
(Phase 11 Batch 1). Exercises the real `_JsonFormatter`/`get_logger()`
against a captured stream -- no mocking of the logging module itself.
"""

import io
import json
import logging

import pytest

from backend.shared.logging.logger import get_logger
from backend.shared.observability.correlation import _request_id_var


def _capture_one_log_line(logger_name: str, log_fn_name: str, *args, **kwargs) -> dict:
    logger = get_logger(logger_name)
    stream = io.StringIO()
    # Swap the real stdout handler's stream for a capturable one, keeping
    # the same _JsonFormatter -- exercises the real formatter, not a copy.
    handler = logger.handlers[0]
    original_stream = handler.stream
    handler.stream = stream
    try:
        getattr(logger, log_fn_name)(*args, **kwargs)
    finally:
        handler.stream = original_stream
    return json.loads(stream.getvalue().strip())


def test_log_output_is_valid_json_with_standard_fields():
    payload = _capture_one_log_line("backend.services.gateway_service.app.core.errors", "info", "Something happened")

    assert payload["message"] == "Something happened"
    assert payload["level"] == "INFO"
    assert payload["service"] == "gateway_service"
    assert payload["logger"] == "backend.services.gateway_service.app.core.errors"
    assert "timestamp" in payload
    # ISO-8601 with a timezone offset -- fromisoformat round-trips it.
    from datetime import datetime

    datetime.fromisoformat(payload["timestamp"])


def test_service_name_is_inferred_from_the_module_path_for_every_known_service():
    cases = {
        "backend.services.recommendation_service.app.presentation.api.recommendations": "recommendation_service",
        "backend.services.business_impact_service.app.services.business_impact_event_publisher": "business_impact_service",
        "backend.services.anomaly_service.app.api.trends": "anomaly_service",
    }
    for logger_name, expected_service in cases.items():
        payload = _capture_one_log_line(logger_name, "info", "x")
        assert payload["service"] == expected_service


def test_service_name_falls_back_to_the_raw_logger_name_outside_backend_services():
    payload = _capture_one_log_line("backend.shared.database.health", "info", "x")
    assert payload["service"] == "backend.shared.database.health"


def test_log_level_is_preserved_across_levels():
    for level_name, log_fn in [("WARNING", "warning"), ("ERROR", "error"), ("DEBUG", "debug")]:
        logger_name = f"backend.services.gateway_service.app.test.{level_name.lower()}"
        logger = get_logger(logger_name)
        logger.setLevel(logging.DEBUG)  # ensure DEBUG isn't filtered out for this assertion
        payload = _capture_one_log_line(logger_name, log_fn, "x")
        assert payload["level"] == level_name


def test_exception_logging_includes_a_formatted_traceback_not_a_raw_object():
    logger_name = "backend.services.gateway_service.app.test.exception"
    logger = get_logger(logger_name)
    stream = io.StringIO()
    handler = logger.handlers[0]
    original_stream = handler.stream
    handler.stream = stream
    try:
        try:
            raise ValueError("boom")
        except ValueError:
            logger.exception("Unhandled error")
    finally:
        handler.stream = original_stream
    payload = json.loads(stream.getvalue().strip())

    assert payload["level"] == "ERROR"
    assert "exception" in payload
    assert isinstance(payload["exception"], str)
    assert "ValueError" in payload["exception"]
    assert "boom" in payload["exception"]


def test_request_id_is_attached_when_a_request_context_is_active():
    token = _request_id_var.set("test-request-id-123")
    try:
        payload = _capture_one_log_line("backend.services.gateway_service.app.test.reqid", "info", "x")
    finally:
        _request_id_var.reset(token)

    assert payload["request_id"] == "test-request-id-123"


def test_request_id_is_omitted_not_null_outside_a_request_context():
    payload = _capture_one_log_line("backend.services.gateway_service.app.test.noreqid", "info", "x")
    assert "request_id" not in payload


def test_safe_extra_fields_are_included_when_explicitly_supplied():
    logger = get_logger("backend.services.gateway_service.app.test.extra")
    stream = io.StringIO()
    handler = logger.handlers[0]
    original_stream = handler.stream
    handler.stream = stream
    try:
        logger.info("Downstream call failed", extra={"safe_extra": {"downstream_url": "http://anomaly_service:8003/health"}})
    finally:
        handler.stream = original_stream
    payload = json.loads(stream.getvalue().strip())

    assert payload["downstream_url"] == "http://anomaly_service:8003/health"


def test_get_logger_never_duplicates_handlers_on_repeated_calls():
    logger_a = get_logger("backend.services.gateway_service.app.test.dedup")
    logger_b = get_logger("backend.services.gateway_service.app.test.dedup")
    assert logger_a is logger_b
    assert len(logger_a.handlers) == 1


@pytest.mark.parametrize(
    "forbidden_term",
    ["password", "secret", "api_key", "authorization"],
)
def test_formatter_does_not_inject_any_field_by_default(forbidden_term):
    """The formatter itself never adds request-body/header/credential content -- only what a caller explicitly logs."""
    payload = _capture_one_log_line("backend.services.gateway_service.app.test.safety", "info", "A normal message")
    assert forbidden_term not in json.dumps(payload).lower()
