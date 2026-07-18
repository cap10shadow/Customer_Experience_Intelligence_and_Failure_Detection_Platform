from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.shared.database.database import engine
from backend.shared.database.health import check_database_connection
from backend.services.nlp_service.app.api.enrichments import router as enrichments_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not await check_database_connection():
        raise RuntimeError("Database connectivity check failed on startup.")
    yield
    await engine.dispose()


app = FastAPI(title="NLP Service", lifespan=lifespan)

app.include_router(enrichments_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "nlp_service"}
