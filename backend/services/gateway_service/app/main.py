from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from backend.services.gateway_service.app.api.administration import router as administration_router
from backend.services.gateway_service.app.api.analytics import router as analytics_router
from backend.services.gateway_service.app.api.dashboard import router as dashboard_router
from backend.services.gateway_service.app.api.investigations import router as investigations_router
from backend.services.gateway_service.app.api.recommendations import router as recommendations_router
from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.core.errors import (
    GatewayError,
    gateway_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from backend.shared.observability.correlation import CorrelationIdMiddleware
from backend.shared.observability.metrics import instrument_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    # One shared client for the app's lifetime, not one per request/route --
    # workspace route modules (Parts 2-5) pull it via
    # app.dependencies.http_client.get_http_client rather than constructing
    # their own. Gateway does not own persistence (Batch 1 §2), so there is
    # deliberately no database engine here.
    app.state.http_client = httpx.AsyncClient(timeout=settings.DOWNSTREAM_TIMEOUT_SECONDS)
    yield
    await app.state.http_client.aclose()


app = FastAPI(title="Gateway Service", lifespan=lifespan)

# Correlation ID must run for every request, including ones that error out
# before reaching a route, so it's added before the error handlers below
# ever need get_request_id() to find something on request.state.
app.add_middleware(CorrelationIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standardized error envelope (Batch 1 §12, Batch 4B §4B-10) for every
# failure path: Gateway-raised domain errors, FastAPI's own request
# validation errors, and anything unhandled.
app.add_exception_handler(GatewayError, gateway_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

# Phase 11 Batch 1: common technical HTTP metrics + GET /metrics. No
# readiness endpoint here -- gateway_service owns no database (Batch 1
# §2 of the Phase 10 record), so it has no dependency of its own to
# check beyond the process being up, which /health below already answers.
instrument_app(app, service_name="gateway_service")

app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(investigations_router, prefix="/api/v1")
app.include_router(recommendations_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(administration_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "gateway_service"}
