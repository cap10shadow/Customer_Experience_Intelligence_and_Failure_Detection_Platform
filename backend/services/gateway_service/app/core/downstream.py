from typing import Any, Optional

import httpx

from backend.services.gateway_service.app.core.errors import (
    DownstreamServiceError,
    DownstreamTimeoutError,
    DownstreamUnavailableError,
)
from backend.shared.observability.correlation import correlation_headers


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
        response = await client.get(url, params=params, headers=correlation_headers())
    except httpx.TimeoutException as exc:
        raise DownstreamTimeoutError(f"Timed out calling {url}.") from exc
    except httpx.RequestError as exc:
        raise DownstreamUnavailableError(f"Could not reach {url}.") from exc

    if response.status_code == 404:
        return None
    if response.status_code >= 400:
        raise DownstreamServiceError(f"{url} returned status {response.status_code}.")
    return response.json()


async def post_json(
    client: httpx.AsyncClient, url: str, *, json: Optional[dict] = None, extra_headers: Optional[dict] = None
) -> Any:
    """
    Issues one bounded POST to a downstream service and returns its
    parsed JSON body, or None for a 404 -- the same contract as
    `get_json()`/`patch_json()` (see their docstrings), reused here so
    every downstream call, regardless of HTTP method, gets identical
    timeout/connection-failure/non-2xx handling and the same standardized
    error envelope.

    `extra_headers` (Phase 13 Batch 4, AD-5): optional, additive headers
    merged in on top of the correlation header -- used only by the two
    calls that need the internal-service credential and/or the
    Gateway-attested principal header (`recommendation_aggregator.
    update_recommendation_decision`, `copilot_aggregator.
    send_copilot_message`). Every other caller passes nothing here and
    is completely unaffected.
    """
    try:
        response = await client.post(url, json=json, headers={**correlation_headers(), **(extra_headers or {})})
    except httpx.TimeoutException as exc:
        raise DownstreamTimeoutError(f"Timed out calling {url}.") from exc
    except httpx.RequestError as exc:
        raise DownstreamUnavailableError(f"Could not reach {url}.") from exc

    if response.status_code == 404:
        return None
    if response.status_code >= 400:
        raise DownstreamServiceError(f"{url} returned status {response.status_code}.")
    return response.json()


async def post_resource(
    client: httpx.AsyncClient, url: str, *, json: Optional[dict] = None, extra_headers: Optional[dict] = None
) -> httpx.Response:
    """
    Issues one bounded POST and returns the raw `httpx.Response` --
    unlike `post_json`, deliberately not status-mapped here (Phase 13
    Batch 6, AD-4). `post_json`'s shared "404 -> None, >=400 ->
    DownstreamServiceError" contract assumes every non-2xx is a genuine
    downstream failure; that assumption doesn't hold for
    `copilot_aggregator.send_copilot_message`, where a `401`/`403` is a
    real, legitimate conversation-ownership outcome (§17) the Gateway
    must translate into its own `AuthenticationError`/`AuthorizationError`,
    not mask behind a generic `502` -- the same reasoning
    `delete_resource` documents for the DELETE conversation route. Only
    connection failure and timeout are handled here -- every status-code
    interpretation is the caller's.
    """
    try:
        return await client.post(url, json=json, headers={**correlation_headers(), **(extra_headers or {})})
    except httpx.TimeoutException as exc:
        raise DownstreamTimeoutError(f"Timed out calling {url}.") from exc
    except httpx.RequestError as exc:
        raise DownstreamUnavailableError(f"Could not reach {url}.") from exc


async def put_resource(
    client: httpx.AsyncClient, url: str, *, json: Optional[dict] = None, extra_headers: Optional[dict] = None
) -> httpx.Response:
    """
    Issues one bounded PUT and returns the raw `httpx.Response`, mirroring
    `post_resource`'s rationale (see its docstring) -- the one current
    caller (`ingestion_proxy.update_alias_suggestion`) needs to translate
    a downstream 422 into the Gateway's own `GatewayValidationError`, not
    have it masked behind a generic 502. Only connection failure and
    timeout are handled here -- every status-code interpretation is the
    caller's.
    """
    try:
        return await client.put(url, json=json, headers={**correlation_headers(), **(extra_headers or {})})
    except httpx.TimeoutException as exc:
        raise DownstreamTimeoutError(f"Timed out calling {url}.") from exc
    except httpx.RequestError as exc:
        raise DownstreamUnavailableError(f"Could not reach {url}.") from exc


async def delete_resource(
    client: httpx.AsyncClient, url: str, *, extra_headers: Optional[dict] = None
) -> httpx.Response:
    """
    Issues one bounded DELETE to a downstream service and returns the
    raw `httpx.Response`, unlike `get_json`/`post_json`/`patch_json` --
    deliberately not parsed/status-mapped here (Phase 13 Batch 6, AD-4).
    Those three helpers' shared "404 -> None, >=400 -> DownstreamServiceError"
    contract assumes every non-2xx/404 status is a genuine downstream
    failure; that assumption doesn't hold for
    `copilot_aggregator.delete_conversation`, where a `401`/`403` is a
    legitimate ownership-boundary outcome the Gateway must translate
    into its own `AuthenticationError`/`AuthorizationError`, not mask
    behind a generic `502`. Only connection failure and timeout are
    handled here -- every status-code interpretation is the caller's.
    """
    try:
        return await client.delete(url, headers={**correlation_headers(), **(extra_headers or {})})
    except httpx.TimeoutException as exc:
        raise DownstreamTimeoutError(f"Timed out calling {url}.") from exc
    except httpx.RequestError as exc:
        raise DownstreamUnavailableError(f"Could not reach {url}.") from exc


async def patch_resource(
    client: httpx.AsyncClient, url: str, *, json: Optional[dict] = None, extra_headers: Optional[dict] = None
) -> httpx.Response:
    """
    Issues one bounded PATCH and returns the raw `httpx.Response` --
    unlike `patch_json`, deliberately not status-mapped here, mirroring
    `post_resource`'s rationale (see its docstring): a caller whose
    downstream resource carries its own real conflict semantics (e.g.
    root_cause_service's 409 on an invalid confirm/reject lifecycle
    transition) must be able to translate that into the Gateway's own
    `ConflictError`, not have it masked behind a generic 502. Only
    connection failure and timeout are handled here -- every status-code
    interpretation is the caller's.
    """
    try:
        return await client.patch(url, json=json, headers={**correlation_headers(), **(extra_headers or {})})
    except httpx.TimeoutException as exc:
        raise DownstreamTimeoutError(f"Timed out calling {url}.") from exc
    except httpx.RequestError as exc:
        raise DownstreamUnavailableError(f"Could not reach {url}.") from exc


async def patch_json(
    client: httpx.AsyncClient, url: str, *, json: Optional[dict] = None, extra_headers: Optional[dict] = None
) -> Any:
    """
    Issues one bounded PATCH to a downstream service and returns its
    parsed JSON body, or None for a 404 -- the same contract as
    `get_json()` (see its docstring), reused here rather than duplicated
    so every downstream call, GET or PATCH, gets identical
    timeout/connection-failure/non-2xx handling and the same standardized
    error envelope. A 422 (the downstream's own request-validation
    failure) is deliberately included in the ">= 400" branch, surfacing
    as a 502 DownstreamServiceError -- the Gateway's own request model
    already validates shape before this call is ever made, so a
    downstream 422 here indicates a genuine contract mismatch, not a
    client input error the Gateway should re-validate.

    `extra_headers` -- see `post_json`'s docstring (Phase 13 Batch 4).
    """
    try:
        response = await client.patch(url, json=json, headers={**correlation_headers(), **(extra_headers or {})})
    except httpx.TimeoutException as exc:
        raise DownstreamTimeoutError(f"Timed out calling {url}.") from exc
    except httpx.RequestError as exc:
        raise DownstreamUnavailableError(f"Could not reach {url}.") from exc

    if response.status_code == 404:
        return None
    if response.status_code >= 400:
        raise DownstreamServiceError(f"{url} returned status {response.status_code}.")
    return response.json()
