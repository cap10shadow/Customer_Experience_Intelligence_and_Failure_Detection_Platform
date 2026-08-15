from typing import Any

from fastapi import status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.requests import Request

from backend.shared.logging.logger import get_logger
from backend.shared.observability.correlation import get_request_id
from backend.shared.observability.metrics import route_template

logger = get_logger(__name__)


class ErrorDetail(BaseModel):
    code: str
    message: str
    requestId: str
    details: Any | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class GatewayError(Exception):
    """
    Base class for errors the Gateway raises intentionally, carrying the
    HTTP status and machine-readable code the frozen error envelope
    (Batch 1 §12, Batch 4B §4B-10) requires. Never carries a stack trace,
    SQL error, credential, or internal hostname in `message`/`details` --
    callers of these subclasses are responsible for keeping the message
    safe to show a browser.
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, details: Any | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class GatewayValidationError(GatewayError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "VALIDATION_ERROR"


class ResourceNotFoundError(GatewayError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "RESOURCE_NOT_FOUND"


class AuthenticationError(GatewayError):
    """
    Phase 13 Batch 2 (AD-6): missing, invalid, or expired session --
    covers both an anonymous request to a protected route and a bad
    login attempt. `message` is always the single generic phrase
    "Invalid email or password." for a failed login (never distinguishes
    unknown-email from wrong-password from inactive-user -- AD-6/§10)
    or "Authentication required." for a missing/expired/invalid session
    -- never a credential, token fragment, or internal detail.
    """

    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHENTICATED"


class AuthorizationError(GatewayError):
    """
    Phase 13 Batch 3 (RBAC, §11/§12): a valid, authenticated session
    that lacks the role a route requires -- distinct from
    `AuthenticationError` (401, "who are you") by design: this is
    always 403 ("I know who you are; you may not do this"). `message`
    is a fixed, generic phrase that never names the caller's actual
    roles or the specific role required -- both would leak authorization
    internals to a client that already isn't supposed to know them.
    """

    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"


class ConflictError(GatewayError):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"


class DownstreamServiceError(GatewayError):
    """The downstream service responded, but with an error (maps to 502)."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "DOWNSTREAM_SERVICE_FAILURE"


class DownstreamUnavailableError(GatewayError):
    """The downstream service could not be reached at all (maps to 503)."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "DOWNSTREAM_SERVICE_UNAVAILABLE"


class DownstreamTimeoutError(GatewayError):
    """The downstream call exceeded its bounded timeout (maps to 504)."""

    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    code = "DOWNSTREAM_TIMEOUT"


def _envelope_response(*, status_code: int, code: str, message: str, request_id: str, details: Any | None = None) -> JSONResponse:
    envelope = ErrorEnvelope(error=ErrorDetail(code=code, message=message, requestId=request_id, details=details))
    return JSONResponse(status_code=status_code, content=envelope.model_dump())


def _log_gateway_error(request: Request, exc: GatewayError) -> None:
    """
    Batch 3 error-visibility: every `GatewayError` is now logged, not just
    unhandled exceptions -- severity follows the same client-vs-server
    split the HTTP status codes already encode, so an expected 4xx (bad
    input, not-found, conflict) never appears as an ERROR-level
    application failure, while a genuine server-side/downstream failure
    (502/503/504) does. Only safe, bounded context is attached (status
    code, error code, route template) -- never the raw downstream
    response body or request payload.
    """
    safe_extra = {
        "status_code": exc.status_code,
        "error_code": exc.code,
        "route": route_template(request),
    }
    if exc.status_code >= 500:
        logger.error(exc.message, extra={"safe_extra": safe_extra})
    else:
        logger.info(exc.message, extra={"safe_extra": safe_extra})


async def gateway_error_handler(request: Request, exc: GatewayError) -> JSONResponse:
    _log_gateway_error(request, exc)
    return _envelope_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request_id=get_request_id(request),
        details=exc.details,
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _envelope_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="The request could not be validated.",
        request_id=get_request_id(request),
        details=None,
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Logged with the full exception for operators; never surfaced to the
    # caller -- the response body stays generic per Batch 1 §12/4B §4B-10
    # ("never expose stack traces, SQL errors, raw exception objects").
    logger.exception("Unhandled Gateway error", exc_info=exc)
    return _envelope_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_ERROR",
        message="An unexpected error occurred.",
        request_id=get_request_id(request),
        details=None,
    )
