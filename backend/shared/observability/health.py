from typing import Dict, Tuple

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from backend.shared.database.health import check_database_connection


async def readiness_check() -> Tuple[bool, Dict[str, str]]:
    """
    Answers "is this service's dependency actually reachable right now,"
    distinct from `/health` (liveness: "is the process up"). Reuses the
    existing `check_database_connection()` primitive verbatim -- this
    module owns only the readiness response shape, not a second
    connectivity-check implementation.
    """
    database_ok = await check_database_connection()
    checks = {"database": "ok" if database_ok else "unavailable"}
    return database_ok, checks


def mount_readiness(app: FastAPI) -> None:
    """
    Mounts `GET /health/ready` on `app`. Only for services that own a
    database (Phase 11 architecture §"Health Architecture") -- of the 9
    backend services, every one except `gateway_service` (which has no
    persistence of its own, per Phase 10 Batch 1 §2). Additive only:
    never replaces or changes the existing `GET /health` liveness route,
    which every service keeps exactly as it is today.
    """

    @app.get("/health/ready", include_in_schema=False)
    async def _readiness() -> JSONResponse:
        ready, checks = await readiness_check()
        return JSONResponse(
            status_code=200 if ready else 503,
            content={"status": "ready" if ready else "not_ready", "checks": checks},
        )
