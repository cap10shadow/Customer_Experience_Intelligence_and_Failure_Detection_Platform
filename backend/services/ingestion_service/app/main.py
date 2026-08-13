from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.services.ingestion_service.app.api.complaints import router as complaints_router
from backend.shared.database.database import engine
from backend.shared.database.health import check_database_connection
from backend.shared.observability.correlation import CorrelationIdMiddleware
from backend.shared.observability.health import mount_readiness
from backend.shared.observability.metrics import instrument_app
from backend.shared.observability.tracing import init_tracing, shutdown_tracing


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not await check_database_connection():
        raise RuntimeError("Database connectivity check failed on startup.")
    yield
    shutdown_tracing()
    await engine.dispose()


app = FastAPI(title="Ingestion Service", lifespan=lifespan)

app.add_middleware(CorrelationIdMiddleware)
instrument_app(app, service_name="ingestion_service")
mount_readiness(app)
init_tracing("ingestion_service", app, engine=engine)

app.include_router(complaints_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ingestion_service"}
