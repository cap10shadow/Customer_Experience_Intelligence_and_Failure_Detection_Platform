from typing import List, Literal

from pydantic import BaseModel

# "healthy" mirrors every backend service's own real `/health` response
# body (`{"status": "ok", "service": "<name>"}`) -- "unavailable" is used
# whenever that call could not be completed (connection failure, timeout,
# or a non-2xx response), never inferred from unrelated data. There is no
# "degraded"/"partial" service-level state today because no backend
# service's own `/health` endpoint reports anything more granular than
# reachable-or-not.
ServiceHealthStatus = Literal["healthy", "unavailable"]


class ServiceHealthDTO(BaseModel):
    """
    One backend service's real, just-checked reachability -- not a
    production observability/uptime-history capability (no metrics
    storage, no historical SLA calculation). Sourced directly from that
    service's own existing `/health` endpoint, called fresh on every
    Platform Overview request.
    """

    id: str
    name: str
    status: ServiceHealthStatus
    detail: str


class AdministrationOverviewResponse(BaseModel):
    services: List[ServiceHealthDTO]
    # Human-readable notes about any service whose health check failed
    # (mirrors Dashboard/Investigation's existing `warnings` convention) --
    # each unavailable service is still represented in `services` above,
    # so this is a supplementary note, not the only signal of the failure.
    warnings: List[str] = []
