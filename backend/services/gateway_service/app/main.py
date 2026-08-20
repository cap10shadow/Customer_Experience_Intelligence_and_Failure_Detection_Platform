from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from backend.services.gateway_service.app.api.administration import router as administration_router
from backend.services.gateway_service.app.api.analytics import router as analytics_router
from backend.services.gateway_service.app.api.auth import router as auth_router
from backend.services.gateway_service.app.api.copilot import router as copilot_router
from backend.services.gateway_service.app.api.dashboard import router as dashboard_router
from backend.services.gateway_service.app.api.datasets import router as datasets_router
from backend.services.gateway_service.app.api.ingestion import router as ingestion_router
from backend.services.gateway_service.app.api.investigations import router as investigations_router
from backend.services.gateway_service.app.api.recommendations import router as recommendations_router
from backend.services.gateway_service.app.core.authorization import require_role
from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.core.errors import (
    GatewayError,
    gateway_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from backend.shared.database.database import engine
from backend.shared.database.health import check_database_connection
from backend.shared.observability.correlation import CorrelationIdMiddleware
from backend.shared.observability.health import mount_readiness, readiness_check
from backend.shared.observability.metrics import instrument_app
from backend.shared.observability.tracing import init_tracing, shutdown_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    # One shared client for the app's lifetime, not one per request/route --
    # workspace route modules (Parts 2-5) pull it via
    # app.dependencies.http_client.get_http_client rather than constructing
    # their own.
    #
    # Phase 13 Batch 1 (AD-1): gateway_service now owns identity
    # persistence (users/roles/user_roles) in the shared PostgreSQL
    # instance -- its first database dependency, matching every other
    # backend service's own startup-check/shutdown-dispose pattern
    # (see ingestion_service/app/main.py). No route in this batch reads
    # or writes through this engine yet; the check only proves the new
    # dependency is reachable before the process starts serving traffic.
    app.state.http_client = httpx.AsyncClient(timeout=settings.DOWNSTREAM_TIMEOUT_SECONDS)
    if not await check_database_connection():
        raise RuntimeError("Database connectivity check failed on startup.")
    yield
    await app.state.http_client.aclose()
    shutdown_tracing()
    await engine.dispose()


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

# Phase 11 Batch 1: common technical HTTP metrics + GET /metrics.
# Phase 13 Batch 1 (AD-1): gateway_service now owns a database
# dependency (identity persistence), so it gains the same
# `/health/ready` + `service_readiness` gauge wiring every other
# DB-owning service already has (backend/shared/observability/health.py)
# -- reusing the existing Phase 11 primitive verbatim, not a new
# observability mechanism. `/health` (liveness) below is unchanged.
instrument_app(app, service_name="gateway_service", refresh_readiness=lambda: readiness_check("gateway_service"))
mount_readiness(app, service_name="gateway_service")
init_tracing("gateway_service", app, engine=engine)

# Phase 13 Batch 2 (AD-6): the public authentication API. Mounted with
# no router-level auth dependency -- /auth/login and /auth/logout must
# stay reachable by an anonymous caller; /auth/me protects itself
# individually (api/auth.py) since it's the one route in this router
# that does require a session.
app.include_router(auth_router, prefix="/api/v1")

# Phase 13 Batch 3 (RBAC, §11/§12's permission matrix): role-based
# authorization, replacing Batch 2's blanket "any authenticated
# session" gate. `require_role("viewer")` is the baseline for every
# read-only router below -- per the matrix, a session with zero roles
# assigned does not satisfy even "viewer", so this is a real role
# check, not merely "is there a valid cookie" (Batch 2's prior
# behavior). `recommendations_router` mixes a viewer-level GET with an
# operator-level PATCH in the same router file, so its PATCH route
# carries its own additional `require_role("operator")` dependency
# directly in `api/recommendations.py` -- the router-level "viewer"
# dependency below still applies to it too (operator already implies
# viewer in the hierarchy, so this is redundant-but-harmless, not a
# conflict). `copilot_router` is entirely operator-level (its one route,
# POST /copilot/messages, per the matrix), so it gets "operator" at the
# router level directly, with no separate per-route override needed.
# `/health`, `/health/ready`, and `/metrics` remain unauthenticated,
# excluded from all of this (mounted above/below).
_require_viewer = [Depends(require_role("viewer"))]
_require_operator = [Depends(require_role("operator"))]
app.include_router(dashboard_router, prefix="/api/v1", dependencies=_require_viewer)
app.include_router(datasets_router, prefix="/api/v1", dependencies=_require_viewer)
app.include_router(ingestion_router, prefix="/api/v1", dependencies=_require_viewer)
app.include_router(investigations_router, prefix="/api/v1", dependencies=_require_viewer)
app.include_router(recommendations_router, prefix="/api/v1", dependencies=_require_viewer)
app.include_router(analytics_router, prefix="/api/v1", dependencies=_require_viewer)
app.include_router(administration_router, prefix="/api/v1", dependencies=_require_viewer)
app.include_router(copilot_router, prefix="/api/v1", dependencies=_require_operator)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "gateway_service"}
