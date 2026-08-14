import httpx
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.copilot_service.app.dependencies.http_client import get_http_client
from backend.services.copilot_service.app.schemas.copilot import CopilotQueryRequest, CopilotQueryResponse
from backend.services.copilot_service.app.services.copilot_query_service import handle_query
from backend.shared.database.session import get_db_session
from backend.shared.observability.correlation import get_request_id

router = APIRouter(tags=["copilot"])


@router.post("/copilot/messages", response_model=CopilotQueryResponse)
async def post_message(
    request: CopilotQueryRequest,
    http_request: Request,
    client: httpx.AsyncClient = Depends(get_http_client),
    session: AsyncSession = Depends(get_db_session),
) -> CopilotQueryResponse:
    """
    Internal-only endpoint, reachable only from gateway_service, never
    the public internet. No business/orchestration logic lives here --
    see copilot_query_service.handle_query's docstring (Phase 12 Batch 4).
    `session` is the one DB session/transaction for this whole request
    (`get_db_session` commits on a normal return, rolls back on any
    exception -- see `conversation_service.handle_persisted_query`'s
    docstring for the transaction-boundary rationale).
    """
    return await handle_query(request, client=client, request_id=get_request_id(http_request), session=session)
