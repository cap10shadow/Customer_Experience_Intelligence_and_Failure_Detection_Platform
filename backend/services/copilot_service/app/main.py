from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.shared.database.database import engine
from backend.shared.database.health import check_database_connection
from backend.shared.observability.correlation import CorrelationIdMiddleware
from backend.shared.observability.health import mount_readiness
from backend.shared.observability.metrics import instrument_app


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not await check_database_connection():
        raise RuntimeError("Database connectivity check failed on startup.")
    yield
    await engine.dispose()


app = FastAPI(title="Copilot Service", lifespan=lifespan)

app.add_middleware(CorrelationIdMiddleware)
instrument_app(app, service_name="copilot_service")
mount_readiness(app)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "copilot_service"}
