from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.shared.database.database import engine
from backend.shared.database.health import check_database_connection
from backend.services.root_cause_service.app.api.root_causes import (
    incidents_router as root_cause_incidents_router,
    router as root_causes_router,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not await check_database_connection():
        raise RuntimeError("Database connectivity check failed on startup.")
    yield
    await engine.dispose()


app = FastAPI(title="Root Cause Service", lifespan=lifespan)

app.include_router(root_causes_router, prefix="/api/v1")
app.include_router(root_cause_incidents_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "root_cause_service"}
