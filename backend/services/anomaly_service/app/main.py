from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.shared.database.database import engine
from backend.shared.database.health import check_database_connection
from backend.services.anomaly_service.app.api.anomalies import router as anomalies_router
from backend.services.anomaly_service.app.api.trends import router as trends_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not await check_database_connection():
        raise RuntimeError("Database connectivity check failed on startup.")
    yield
    await engine.dispose()


app = FastAPI(title="Anomaly Service", lifespan=lifespan)

app.include_router(trends_router, prefix="/api/v1")
app.include_router(anomalies_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "anomaly_service"}
