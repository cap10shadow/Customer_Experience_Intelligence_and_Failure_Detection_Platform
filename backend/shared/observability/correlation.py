import uuid
from contextvars import ContextVar
from typing import Dict, Optional

from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

CORRELATION_HEADER = "X-Request-ID"

# Module-level so both the middleware (writer) and the structured logger /
# outbound-call helpers (readers) share the same context -- readable from
# anywhere in the current request's call stack without threading `Request`
# through every function signature.
_request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Assigns every request a correlation/request ID: reuses one supplied by
    the caller (so a frontend-generated ID, or an upstream service's
    forwarded ID, survives through to logs and any error envelope's
    requestId), or generates one otherwise. Stored on request.state
    .request_id for handlers/logging that only have `request`, and in
    `_request_id_var` for code that has neither (the structured logger,
    outbound downstream HTTP calls). Echoed back on the response so the
    caller can correlate it with server-side logs.

    Phase 11 Batch 1 (OBS-001): promoted from gateway_service's own former
    `core/correlation.py` into this shared, cross-service primitive --
    every service installs this same middleware now, not just the
    Gateway, so correlation IDs propagate across service boundaries
    rather than existing only at the Gateway edge.

    Phase 11 Batch 2 (minimum additive change, not a redesign): also
    attaches `request_id` as an attribute on the current OTel span -- the
    FastAPI instrumentor's inbound server span, when tracing is active
    (`backend.shared.observability.tracing`). This is the one place
    application/log correlation (`request_id`) and distributed tracing
    (`trace_id`, owned entirely by the OTel SDK) intersect: a human
    reading one structured log line can jump straight to its full trace
    without the two ever being treated as the same identifier. A no-op,
    never an error, when tracing is disabled -- `trace.get_current_span()`
    returns a harmless no-op span in that case, per the OTel API's own
    documented contract.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(CORRELATION_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id
        trace.get_current_span().set_attribute("request_id", request_id)
        token = _request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            _request_id_var.reset(token)
        response.headers[CORRELATION_HEADER] = request_id
        return response


def get_request_id(request: Request) -> str:
    """Best-effort accessor for handlers/exception handlers that only have `request`."""
    return getattr(request.state, "request_id", "unknown")


def get_current_request_id() -> Optional[str]:
    """
    Best-effort accessor for code with no `Request` object at all -- the
    structured logger, or an outbound httpx call made deep inside a
    service's call stack. Returns None outside of an active request (e.g.
    at process startup), never a fabricated placeholder ID.
    """
    return _request_id_var.get()


def correlation_headers() -> Dict[str, str]:
    """
    Builds the header dict to attach to an outbound downstream HTTP call
    so the current request's ID threads through to the next service's own
    `CorrelationIdMiddleware` (which reuses an inbound X-Request-ID rather
    than minting a new, disconnected one). Empty when no request is
    currently active -- never sends a fabricated ID.
    """
    request_id = get_current_request_id()
    return {CORRELATION_HEADER: request_id} if request_id else {}
