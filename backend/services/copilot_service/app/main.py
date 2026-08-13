from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.services.copilot_service.app.api.copilot import router as copilot_router
from backend.shared.database.database import engine
from backend.shared.database.health import check_database_connection
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


app = FastAPI(title="Copilot Service", lifespan=lifespan)

app.add_middleware(CorrelationIdMiddleware)
instrument_app(app, service_name="copilot_service", refresh_readiness=lambda: readiness_check("copilot_service"))
mount_readiness(app, service_name="copilot_service")
mount_unhandled_exception_logging(app)
init_tracing("copilot_service", app, engine=engine)

app.include_router(copilot_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "copilot_service"}
