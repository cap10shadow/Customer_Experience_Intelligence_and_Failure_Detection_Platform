import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

CORRELATION_HEADER = "X-Request-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Assigns every request a correlation/request ID: reuses one supplied by
    the caller (so a frontend-generated ID survives through to logs and
    the error envelope's requestId), or generates one otherwise. Stored on
    request.state.request_id for handlers/logging to read, and echoed back
    on the response so the caller can correlate it with server-side logs.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(CORRELATION_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers[CORRELATION_HEADER] = request_id
        return response


def get_request_id(request: Request) -> str:
    """Best-effort accessor for handlers/exception handlers that only have `request`."""
    return getattr(request.state, "request_id", "unknown")
