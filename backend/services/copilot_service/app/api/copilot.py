from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.copilot_service.app.dependencies.http_client import get_http_client
from backend.services.copilot_service.app.schemas.copilot import CopilotQueryRequest, CopilotQueryResponse
from backend.services.copilot_service.app.services.copilot_query_service import handle_query
from backend.shared.database.session import get_db_session
from backend.shared.logging.logger import get_logger
from backend.shared.observability.correlation import get_request_id
from backend.shared.security.internal_auth import PRINCIPAL_USER_ID_HEADER, require_internal_secret

router = APIRouter(tags=["copilot"])
logger = get_logger(__name__)


@router.post("/copilot/messages", response_model=CopilotQueryResponse, dependencies=[Depends(require_internal_secret)])
async def post_message(
    request: CopilotQueryRequest,
    http_request: Request,
    client: httpx.AsyncClient = Depends(get_http_client),
    session: AsyncSession = Depends(get_db_session),
    x_authenticated_user_id: Optional[str] = Header(default=None, alias=PRINCIPAL_USER_ID_HEADER),
) -> CopilotQueryResponse:
    """
    Internal-only endpoint, reachable only from gateway_service, never
    the public internet. No business/orchestration logic lives here --
    see copilot_query_service.handle_query's docstring (Phase 12 Batch 4).
    `session` is the one DB session/transaction for this whole request
    (`get_db_session` commits on a normal return, rolls back on any
    exception -- see `conversation_service.handle_persisted_query`'s
    docstring for the transaction-boundary rationale).

    Phase 13 Batch 4 (AD-5, §14): requires `X-Internal-Secret` -- no
    longer network-topology-protection-only. `x_authenticated_user_id`
    is the Gateway-attested principal, trustworthy only because it
    arrives alongside a valid internal secret; logged only (a safe,
    allowed structured-log field per Phase 11 §23) and never persisted
    -- no `owner_id` column exists yet (explicitly a later batch's
    scope, COPILOT-002/AD-4). The seven read-only tools, LangGraph
    orchestration, and `CopilotResponse` contract are untouched.
    """
    if x_authenticated_user_id:
        logger.info(
            "Copilot query received with a Gateway-attested principal.",
            extra={"safe_extra": {"user_id": x_authenticated_user_id}},
        )
    return await handle_query(request, client=client, request_id=get_request_id(http_request), session=session)
