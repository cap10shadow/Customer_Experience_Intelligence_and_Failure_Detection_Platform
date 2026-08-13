from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.shared.database.database import engine
from backend.shared.database.health import check_database_connection
from backend.services.recommendation_service.app.presentation.api.recommendations import router as recommendations_router
from backend.services.recommendation_service.app.presentation.api.internal_events import (
    router as internal_events_router,
)
from backend.shared.observability.correlation import CorrelationIdMiddleware
from backend.shared.observability.error_logging import mount_unhandled_exception_logging
from backend.shared.observability.health import mount_readiness, readiness_check
from backend.shared.observability.metrics import instrument_app
from backend.shared.observability.tracing import init_tracing, shutdown_tracing


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not await check_database_connection():
        raise RuntimeError("Database connectivity check failed on startup.")
    yield
    shutdown_tracing()
    await engine.dispose()


app = FastAPI(title="Recommendation Service", lifespan=lifespan)

app.add_middleware(CorrelationIdMiddleware)
instrument_app(
    app, service_name="recommendation_service", refresh_readiness=lambda: readiness_check("recommendation_service")
)
mount_readiness(app, service_name="recommendation_service")
mount_unhandled_exception_logging(app)
init_tracing("recommendation_service", app, engine=engine)

app.include_router(recommendations_router, prefix="/api/v1")
app.include_router(internal_events_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "recommendation_service"}
