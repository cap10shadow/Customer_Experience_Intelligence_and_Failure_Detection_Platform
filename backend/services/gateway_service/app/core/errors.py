from typing import Any

from fastapi import status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.requests import Request

from backend.shared.logging.logger import get_logger
from backend.shared.observability.correlation import get_request_id

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


async def gateway_error_handler(request: Request, exc: GatewayError) -> JSONResponse:
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
