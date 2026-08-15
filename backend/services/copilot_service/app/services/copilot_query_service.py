from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.copilot_service.app.schemas.copilot import CopilotQueryRequest, CopilotQueryResponse
from backend.services.copilot_service.app.services.conversation_service import handle_persisted_query


async def handle_query(
    request: CopilotQueryRequest,
    *,
    client: httpx.AsyncClient,
    request_id: str,
    session: AsyncSession,
    actor_id: Optional[UUID],
) -> CopilotQueryResponse:
    """
    Phase 12 Batch 4: delegates to `conversation_service.handle_persisted_query`,
    which loads/creates the conversation, appends the user message, runs
    the bounded LangGraph orchestration turn (Batch 3), appends the
    assistant response, and returns the frozen `CopilotResponse`. With no
    LLM provider configured (`NullLLMProvider`, the default in this
    environment -- verified: no LLM credentials exist anywhere in this
    repository), the orchestrator itself produces the honest "no language
    model configured" answer; this function has no placeholder text of
    its own.

    Phase 13 Batch 6 (AD-4): `actor_id` is passed straight through to
    `handle_persisted_query` -- see that function's and
    `_resolve_conversation`'s docstrings for the full ownership
    contract.
    """
    return await handle_persisted_query(request, client=client, request_id=request_id, session=session, actor_id=actor_id)
