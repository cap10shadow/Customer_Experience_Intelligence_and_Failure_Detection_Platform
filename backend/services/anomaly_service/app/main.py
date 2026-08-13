from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.shared.database.database import engine
from backend.shared.database.health import check_database_connection
from backend.services.anomaly_service.app.api.anomalies import router as anomalies_router
from backend.services.anomaly_service.app.api.incidents import router as incidents_router
from backend.services.anomaly_service.app.api.trends import router as trends_router
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


app = FastAPI(title="Anomaly Service", lifespan=lifespan)

app.add_middleware(CorrelationIdMiddleware)
instrument_app(app, service_name="anomaly_service")
mount_readiness(app)
init_tracing("anomaly_service", app, engine=engine)

app.include_router(trends_router, prefix="/api/v1")
app.include_router(anomalies_router, prefix="/api/v1")
app.include_router(incidents_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "anomaly_service"}
