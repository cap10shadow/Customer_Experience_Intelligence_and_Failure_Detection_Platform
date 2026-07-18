from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.services.ingestion_service.app.api.complaints import router as complaints_router
from backend.shared.database.database import engine
from backend.shared.database.health import check_database_connection


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not await check_database_connection():
        raise RuntimeError("Database connectivity check failed on startup.")
    yield
    await engine.dispose()


app = FastAPI(title="Ingestion Service", lifespan=lifespan)

app.include_router(complaints_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ingestion_service"}
