import httpx
from starlette.requests import Request


def get_http_client(request: Request) -> httpx.AsyncClient:
    """
    Returns the single httpx.AsyncClient created once in the app's
    lifespan (main.py) -- mirrors gateway_service's own
    dependencies/http_client.py exactly. Used by the orchestrator to
    reach the domain services through the existing Batch 2 Tool
    Registry; never constructed per-request.
    """
    return request.app.state.http_client
