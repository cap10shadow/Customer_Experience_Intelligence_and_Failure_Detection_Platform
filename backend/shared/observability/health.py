from typing import Dict, Tuple

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from prometheus_client import Gauge

from backend.shared.database.health import check_database_connection

# Phase 11 closure -- Platform Health readiness panel. A single bounded
# label (`service`), no request/incident/recommendation identifier --
# same label discipline as the shared HTTP metrics (metrics.py). Owned
# here, not metrics.py, since this module already owns readiness
# semantics; `readiness_check()` is the one place that computes
# freshness, so both `/health/ready` and a `/metrics` scrape (see
# `instrument_app(..., refresh_readiness=...)`, metrics.py) update the
# same value from the same check -- no second connectivity-check
# implementation.
SERVICE_READINESS = Gauge(
    "service_readiness",
    "1 if this service's last dependency check passed, 0 otherwise",
    ["service"],
)


async def readiness_check(service_name: str) -> Tuple[bool, Dict[str, str]]:
    """
    Answers "is this service's dependency actually reachable right now,"
    distinct from `/health` (liveness: "is the process up"). Reuses the
    existing `check_database_connection()` primitive verbatim -- this
    module owns only the readiness response shape, not a second
    connectivity-check implementation. Also updates `SERVICE_READINESS`
    so the same real check is visible to Prometheus/Grafana, not just to
    a caller of `/health/ready` directly.
    """
    database_ok = await check_database_connection()
    SERVICE_READINESS.labels(service=service_name).set(1 if database_ok else 0)
    checks = {"database": "ok" if database_ok else "unavailable"}
    return database_ok, checks


def mount_readiness(app: FastAPI, service_name: str) -> None:
    """
    Mounts `GET /health/ready` on `app`. Only for services that own a
    database (Phase 11 architecture §"Health Architecture") -- of the 9
    backend services, every one except `gateway_service` (which has no
    persistence of its own, per Phase 10 Batch 1 §2). Additive only:
    never replaces or changes the existing `GET /health` liveness route,
    and the `/health/ready` JSON response shape is unchanged from Batch 1
    -- `service_name` is used only to label the Prometheus gauge, never
    added to the response body.
    """

    @app.get("/health/ready", include_in_schema=False)
    async def _readiness() -> JSONResponse:
        ready, checks = await readiness_check(service_name)
        return JSONResponse(
            status_code=200 if ready else 503,
            content={"status": "ready" if ready else "not_ready", "checks": checks},
        )
