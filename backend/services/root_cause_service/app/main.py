from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.shared.database.database import engine
from backend.shared.database.health import check_database_connection


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not await check_database_connection():
        raise RuntimeError("Database connectivity check failed on startup.")
    yield
    await engine.dispose()


app = FastAPI(title="Root Cause Service", lifespan=lifespan)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "root_cause_service"}
