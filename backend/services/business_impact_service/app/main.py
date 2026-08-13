from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from backend.services.business_impact_service.app.api.business_impact import router as business_impact_router
from backend.services.business_impact_service.app.api.configuration import router as configuration_router
from backend.services.business_impact_service.app.core.config import settings
from backend.shared.database.database import engine
from backend.shared.database.health import check_database_connection
from backend.shared.observability.correlation import CorrelationIdMiddleware
from backend.shared.observability.error_logging import mount_unhandled_exception_logging
from backend.shared.observability.health import mount_readiness
from backend.shared.observability.metrics import instrument_app
from backend.shared.observability.tracing import init_tracing, shutdown_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not await check_database_connection():
        raise RuntimeError("Database connectivity check failed on startup.")
    # One shared client for the app's lifetime (Part 6) -- used only to
    # deliver BusinessImpactCompleted to recommendation_service/
    # evaluation_service; see dependencies/services.py's get_http_client.
    # httpx instrumentation (init_tracing, below) is process-wide, so this
    # client's outbound calls are traced automatically -- this is the
    # BusinessImpactCompleted event-delivery trace boundary (Phase 11
    # architecture F6): no service-specific tracing code needed here.
    app.state.http_client = httpx.AsyncClient(timeout=settings.EVENT_DELIVERY_TIMEOUT_SECONDS)
    yield
    await app.state.http_client.aclose()
    shutdown_tracing()
    await engine.dispose()


app = FastAPI(title="Business Impact Service", lifespan=lifespan)

app.add_middleware(CorrelationIdMiddleware)
instrument_app(app, service_name="business_impact_service")
mount_readiness(app)
mount_unhandled_exception_logging(app)
init_tracing("business_impact_service", app, engine=engine)

app.include_router(business_impact_router, prefix="/api/v1")
app.include_router(configuration_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "business_impact_service"}
