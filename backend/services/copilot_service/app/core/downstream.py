from typing import Any, Literal, Optional

import httpx

from backend.shared.observability.correlation import correlation_headers

ToolFailureKind = Literal["timeout", "unavailable", "service_error"]


class ToolError(Exception):
    """
    Raised by `get_json` on a genuine downstream failure (never for a
    legitimate 404, which returns None -- the same "absence vs. failure"
    distinction gateway_service/app/core/downstream.py already
    establishes). Carries a safe, bounded `kind`/message only -- never
    the raw exception, response body, or headers -- for tool adapters to
    convert into an honest, structured tool-level failure (Phase 12
    architecture §22) rather than a fabricated result.
    """

    def __init__(self, message: str, *, kind: ToolFailureKind) -> None:
        super().__init__(message)
        self.message = message
        self.kind = kind


async def get_json(client: httpx.AsyncClient, url: str, *, params: Optional[dict] = None) -> Any:
    """
    Issues one bounded, read-only GET to a domain service and returns its
    parsed JSON body, or None for a 404 (a legitimate absence -- e.g. an
    incident with no RootCause yet -- never a failure). This module
    deliberately exposes no POST/PUT/PATCH/DELETE helper: Copilot's tool
    registry can structurally never mutate anything through this client,
    not merely by convention (Phase 12 architecture §12).
    """
    try:
        response = await client.get(url, params=params, headers=correlation_headers())
    except httpx.TimeoutException as exc:
        raise ToolError(f"Timed out calling {url}.", kind="timeout") from exc
    except httpx.RequestError as exc:
        raise ToolError(f"Could not reach {url}.", kind="unavailable") from exc

    if response.status_code == 404:
        return None
    if response.status_code >= 400:
        raise ToolError(f"{url} returned status {response.status_code}.", kind="service_error")
    return response.json()
