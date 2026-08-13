import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from backend.shared.config.settings import settings
from backend.shared.observability.correlation import get_current_request_id

_SERVICE_SEGMENT_PREFIX = "backend.services."


def _infer_service_name(logger_name: str) -> str:
    """
    Derives the owning service's name from a `__name__`-style dotted
    module path (e.g. "backend.services.recommendation_service.app...."
    -> "recommendation_service") -- every module in this repository
    already follows this convention (verified: `backend/services/<name>/
    app/...`), so no service needs to separately register its own name.
    Falls back to the raw logger name for anything outside
    `backend.services.*` (e.g. `backend.shared.*` utility code logging
    about itself).
    """
    if logger_name.startswith(_SERVICE_SEGMENT_PREFIX):
        remainder = logger_name[len(_SERVICE_SEGMENT_PREFIX):]
        return remainder.split(".", 1)[0]
    return logger_name


class _JsonFormatter(logging.Formatter):
    """
    Structured JSON log formatter (Phase 11 Batch 1). One JSON object per
    line: `timestamp`, `level`, `service`, `logger`, `message`, plus
    `request_id` when a request is currently active and `exception` when
    logged with `exc_info`. Never serializes a raw exception object,
    request body, header, or credential -- only the exception's standard
    formatted traceback text (safe, human-readable) -- the same "never
    expose stack traces [to callers], SQL errors, raw exception objects"
    discipline the Gateway's own error envelope already established
    (`gateway_service/app/core/errors.py`), applied here to what gets
    *logged*, not just what a caller sees in an HTTP response.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "service": _infer_service_name(record.name),
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = get_current_request_id()
        if request_id:
            payload["request_id"] = request_id

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Callers may pass `extra={"safe_extra": {...}}` to attach
        # additional structured fields -- deliberately opt-in and
        # explicitly named "safe_extra" (not merged from arbitrary
        # LogRecord attributes) so nothing a caller didn't consciously
        # choose to log ever reaches the structured output.
        safe_extra = getattr(record, "safe_extra", None)
        if isinstance(safe_extra, dict):
            payload.update(safe_extra)

        return json.dumps(payload, default=str)


def get_logger(name: str) -> logging.Logger:
    """
    The one shared structured-logging entry point every service imports
    (Phase 11 Batch 1) -- same `get_logger(__name__)` call signature as
    before this rewrite, now emitting one JSON object per line to stdout
    instead of a plain-text line. `request_id` is attached automatically
    from the active request's contextvar (see
    `backend.shared.observability.correlation`) when one exists -- never
    a fabricated ID otherwise (e.g. at process startup).
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
        # Docker/uvicorn's own root-logger handlers would otherwise also
        # emit this record (unstructured) via propagation, duplicating
        # every line -- this was never actually exercised before this
        # rewrite (nothing called get_logger()), so this is a new,
        # correctness-only addition, not a change to prior behavior.
        logger.propagate = False
    return logger
