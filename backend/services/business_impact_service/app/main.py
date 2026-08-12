from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from backend.services.business_impact_service.app.api.business_impact import router as business_impact_router
from backend.services.business_impact_service.app.core.config import settings
from backend.shared.database.database import engine
from backend.shared.database.health import check_database_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not await check_database_connection():
        raise RuntimeError("Database connectivity check failed on startup.")
    # One shared client for the app's lifetime (Part 6) -- used only to
    # deliver BusinessImpactCompleted to recommendation_service/
    # evaluation_service; see dependencies/services.py's get_http_client.
    app.state.http_client = httpx.AsyncClient(timeout=settings.EVENT_DELIVERY_TIMEOUT_SECONDS)
    yield
    await app.state.http_client.aclose()
    await engine.dispose()


app = FastAPI(title="Business Impact Service", lifespan=lifespan)

app.include_router(business_impact_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "business_impact_service"}
