from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.shared.database.database import engine
from backend.shared.database.health import check_database_connection
from backend.services.business_impact_service.app.api.business_impact import router as business_impact_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not await check_database_connection():
        raise RuntimeError("Database connectivity check failed on startup.")
    yield
    await engine.dispose()


app = FastAPI(title="Business Impact Service", lifespan=lifespan)

app.include_router(business_impact_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "business_impact_service"}
