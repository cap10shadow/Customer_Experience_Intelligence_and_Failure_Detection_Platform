import hmac
from typing import Optional

from fastapi import Header, HTTPException, status

from backend.shared.config.settings import settings

"""
The platform's one internal service-to-service trust primitive (Phase
13 Batch 4 -- AD-5, docs/architecture/phase-13/PHASE_13_ARCHITECTURE.md
§13/§14). Lives in `backend/shared`, not any one service, because
multiple services both send and receive this header: business_impact_
service and gateway_service (senders), recommendation_service,
evaluation_service, and copilot_service (receivers).

This is a SEPARATE trust domain from human authentication (AD-1/AD-6,
Gateway's JWT session cookie). A service holding this shared secret is
never treated as a human principal, and a human's session cookie is
never accepted here -- the two must never be interchangeable.

Deliberately the ONE mechanism: no JWT-between-services, no mTLS, no
service mesh, no per-service credential. `X-Internal-Secret` is a
single, shared, env-injected value every legitimate internal caller
already knows; the receiving side never distinguishes "missing" from
"wrong" in its response, and never falls back to trusting an unsigned
request just because it arrived over the Docker network.
"""

INTERNAL_SECRET_HEADER = "X-Internal-Secret"
PRINCIPAL_USER_ID_HEADER = "X-Authenticated-User-Id"


def internal_service_headers() -> dict:
    """
    The one place a caller builds the internal-secret header value --
    `business_impact_event_publisher.py` and the Gateway's own outbound
    calls both use this rather than each constructing the header dict
    by hand, so the header name can never drift between sender and
    receiver.
    """
    return {INTERNAL_SECRET_HEADER: settings.INTERNAL_SERVICE_SECRET}


async def require_internal_secret(
    x_internal_secret: Optional[str] = Header(default=None, alias=INTERNAL_SECRET_HEADER),
) -> None:
    """
    Fails closed. A missing header, an empty header, and a mismatched
    value all raise the identical generic 401 -- never distinguishing
    which occurred, so a response can never be used to probe toward a
    valid secret. Uses `hmac.compare_digest` (constant-time) rather than
    `==`, since even a prototype shared-secret comparison should not be
    timing-attackable by construction.
    """
    if not x_internal_secret or not hmac.compare_digest(x_internal_secret, settings.INTERNAL_SERVICE_SECRET):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized.")
