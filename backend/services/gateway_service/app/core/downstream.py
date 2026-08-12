from typing import Any, Optional

import httpx

from backend.services.gateway_service.app.core.errors import (
    DownstreamServiceError,
    DownstreamTimeoutError,
    DownstreamUnavailableError,
)


async def get_json(client: httpx.AsyncClient, url: str, *, params: Optional[dict] = None) -> Any:
    """
    Issues one bounded GET to a downstream service and returns its parsed
    JSON body, or None for a 404 -- a legitimate "not found" (e.g. an
    incident with no RootCause yet), not a failure. Every other failure
    mode -- connection failure, timeout, non-2xx -- is translated into the
    matching GatewayError subclass so the standardized error envelope and
    502/503/504 status mapping apply uniformly regardless of which
    downstream service is involved. Timeout itself is bounded by the
    shared httpx.AsyncClient's configured timeout (GatewaySettings.
    DOWNSTREAM_TIMEOUT_SECONDS), not per-call here.
    """
    try:
        response = await client.get(url, params=params)
    except httpx.TimeoutException as exc:
        raise DownstreamTimeoutError(f"Timed out calling {url}.") from exc
    except httpx.RequestError as exc:
        raise DownstreamUnavailableError(f"Could not reach {url}.") from exc

    if response.status_code == 404:
        return None
    if response.status_code >= 400:
        raise DownstreamServiceError(f"{url} returned status {response.status_code}.")
    return response.json()
