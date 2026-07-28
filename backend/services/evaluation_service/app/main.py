from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.shared.database.database import engine
from backend.shared.database.health import check_database_connection
from backend.services.evaluation_service.app.presentation.api.evaluations import router as evaluations_router
from backend.services.evaluation_service.app.presentation.api.internal_events import (
    router as internal_events_router,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not await check_database_connection():
        raise RuntimeError("Database connectivity check failed on startup.")
    yield
    await engine.dispose()


app = FastAPI(title="Evaluation Service", lifespan=lifespan)

app.include_router(evaluations_router, prefix="/api/v1")
app.include_router(internal_events_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "evaluation_service"}
