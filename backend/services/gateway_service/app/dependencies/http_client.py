import httpx
from starlette.requests import Request


def get_http_client(request: Request) -> httpx.AsyncClient:
    """
    Returns the single httpx.AsyncClient created once in the app's
    lifespan (backend/services/gateway_service/app/main.py) and stored on
    app.state -- not a new client per request. The client is constructed
    with GatewaySettings.DOWNSTREAM_TIMEOUT_SECONDS as a bounded timeout
    covering connect/read/write/pool, so no downstream call the Gateway
    makes through it can hang indefinitely (Batch 1 §13).

    Workspace route modules (Parts 2-5) depend on this to reach the eight
    downstream services; this module intentionally contains no routing or
    aggregation logic of its own.
    """
    return request.app.state.http_client
