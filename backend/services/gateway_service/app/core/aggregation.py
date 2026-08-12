import asyncio
from typing import Optional, TypeVar

from backend.services.gateway_service.app.core.errors import GatewayError

T = TypeVar("T")


async def await_optional(
    task: "asyncio.Task[T]", warnings: list[str], message: str, *, default: Optional[T] = None
) -> Optional[T]:
    """
    Awaits a non-essential downstream task: a GatewayError (transport
    failure or non-2xx from the downstream service) degrades to `default`
    with a human-readable note appended to `warnings`, rather than failing
    the whole aggregate response. Essential dependencies should be
    awaited directly instead, so their GatewayError propagates uncaught.
    """
    try:
        return await task
    except GatewayError as exc:
        warnings.append(f"{message} ({exc.code})")
        return default
