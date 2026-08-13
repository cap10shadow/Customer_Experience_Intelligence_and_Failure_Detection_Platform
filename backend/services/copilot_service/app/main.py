from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from backend.services.copilot_service.app.api.copilot import router as copilot_router
from backend.services.copilot_service.app.services.orchestrator.graph import TOOL_CALL_TIMEOUT_SECONDS
from backend.shared.database.database import engine
from backend.shared.database.health import check_database_connection
from backend.shared.observability.correlation import CorrelationIdMiddleware
from backend.shared.observability.error_logging import mount_unhandled_exception_logging
from backend.shared.observability.health import mount_readiness, readiness_check
from backend.shared.observability.metrics import instrument_app
from backend.shared.observability.tracing import init_tracing, shutdown_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not await check_database_connection():
        raise RuntimeError("Database connectivity check failed on startup.")
    # One shared client for the app's lifetime (Phase 12 Batch 3) -- the
    # orchestrator's tool adapters (Batch 2) pull it via
    # dependencies/http_client.get_http_client, mirroring
    # gateway_service's identical pattern. Bounded timeout covers every
    # tool call (architecture §19).
    app.state.http_client = httpx.AsyncClient(timeout=TOOL_CALL_TIMEOUT_SECONDS)
    yield
    await app.state.http_client.aclose()
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
