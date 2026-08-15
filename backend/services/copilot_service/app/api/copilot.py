import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.copilot_service.app.dependencies.http_client import get_http_client
from backend.services.copilot_service.app.repositories.conversation_repository import CopilotConversationRepository
from backend.services.copilot_service.app.schemas.copilot import CopilotQueryRequest, CopilotQueryResponse
from backend.services.copilot_service.app.services.conversation_service import delete_conversation
from backend.services.copilot_service.app.services.copilot_query_service import handle_query
from backend.shared.database.session import get_db_session
from backend.shared.logging.logger import get_logger
from backend.shared.observability.correlation import get_request_id
from backend.shared.security.internal_auth import PRINCIPAL_USER_ID_HEADER, require_internal_secret

router = APIRouter(tags=["copilot"])
logger = get_logger(__name__)


def _parse_actor_id(x_authenticated_user_id: Optional[str]) -> Optional[uuid.UUID]:
    """
    Shared header-parsing helper for every route in this module (Phase
    13 Batch 6, AD-4). A missing header parses to `None`; a malformed
    one (not a valid UUID) also degrades to `None` rather than raising
    here -- the same "never crash on a malformed attested header, let
    the ownership check downstream decide" discipline
    `recommendation_service`'s own `PATCH .../decision` route already
    established (Phase 13 Batch 5). `None` ultimately becomes a `401`
    inside `conversation_service`, not a `422` here.
    """
    if not x_authenticated_user_id:
        return None
    try:
        return uuid.UUID(x_authenticated_user_id)
    except ValueError:
        return None


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
    longer network-topology-protection-only.

    Phase 13 Batch 6 (AD-4, §16/§17): `x_authenticated_user_id` is the
    Gateway-attested principal, trustworthy only because it arrives
    alongside a valid internal secret; logged (a safe, allowed
    structured-log field per Phase 11 §23) and now also passed as
    `actor_id` into the real ownership-enforcing path
    (`handle_query` -> `handle_persisted_query` -> `_resolve_conversation`),
    which raises `401`/`403` per that function's own contract. The
    seven read-only tools, LangGraph orchestration, and
    `CopilotResponse` contract are untouched.
    """
    actor_id = _parse_actor_id(x_authenticated_user_id)
    if x_authenticated_user_id:
        logger.info(
            "Copilot query received with a Gateway-attested principal.",
            extra={"safe_extra": {"user_id": x_authenticated_user_id}},
        )
    return await handle_query(
        request, client=client, request_id=get_request_id(http_request), session=session, actor_id=actor_id
    )


@router.delete(
    "/copilot/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_internal_secret)],
)
async def delete_copilot_conversation(
    conversation_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    x_authenticated_user_id: Optional[str] = Header(default=None, alias=PRINCIPAL_USER_ID_HEADER),
) -> Response:
    """
    Internal-only endpoint, reachable only from gateway_service (Phase
    13 Batch 6, AD-4, §17/§18): deletes one Copilot conversation
    (cascading to its messages -- see `CopilotConversationRepository
    .delete`'s docstring), scoped to the owning user only, no
    admin-override. `404` if the conversation genuinely does not exist,
    `403` if it exists but `x_authenticated_user_id` isn't its owner
    (including a pre-Phase-13/orphaned conversation with no owner at
    all), `401` if no principal header is present -- see
    `conversation_service.delete_conversation`'s docstring for the full
    contract. `204` on success, no body.
    """
    actor_id = _parse_actor_id(x_authenticated_user_id)
    conversation_repository = CopilotConversationRepository(session)
    await delete_conversation(conversation_id, actor_id=actor_id, conversation_repository=conversation_repository)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
