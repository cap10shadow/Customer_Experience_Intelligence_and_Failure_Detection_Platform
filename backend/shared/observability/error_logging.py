from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from backend.shared.logging.logger import get_logger

logger = get_logger(__name__)


async def _unhandled_exception_handler(request: Request, exc: Exception) -> PlainTextResponse:
    """
    Phase 11 Batch 3: adds structured-log visibility to a genuinely
    unexpected exception on the 8 non-Gateway services (gateway_service
    already logs its own unhandled exceptions via
    `core/errors.py::unhandled_error_handler`). Returns exactly the
    response Starlette's own `ServerErrorMiddleware` already produced for
    these services before this handler existed --
    `PlainTextResponse("Internal Server Error", 500)` -- so no service's
    existing response contract changes; this is visibility-only. Only the
    exception's type/traceback (via `exc_info`) is logged, never a raw
    request body, header, or the exception object itself, matching the
    same discipline the Gateway's own handler already applies.
    """
    logger.error("Unhandled exception", exc_info=exc)
    return PlainTextResponse("Internal Server Error", status_code=500)


def mount_unhandled_exception_logging(app: FastAPI) -> None:
    """
    Mounts the generic-exception logging handler on `app`. FastAPI/
    Starlette resolve exception handlers by walking each exception's own
    MRO, so this never intercepts `HTTPException`/`RequestValidationError`
    (each already has its own, more specific default handler) -- only a
    truly unhandled exception reaches this one.
    """
    app.add_exception_handler(Exception, _unhandled_exception_handler)
