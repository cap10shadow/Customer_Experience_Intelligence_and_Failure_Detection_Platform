"""
Phase 12 Batch 4 -- conversation persistence integration (architecture
§17, COPILOT-002). Wraps the Batch 3 orchestrator with the
load-or-create / append-user / append-assistant flow:

    Gateway -> Copilot API -> load conversation context -> append user
    message -> existing LangGraph orchestration -> synthesize response
    -> append assistant response -> return CopilotResponse

Transaction boundary: the caller (`api/copilot.py`, via
`Depends(get_db_session)`) provides one `AsyncSession` for the whole
HTTP request. That session's transaction commits only if this entire
function returns normally; any exception here -- including one that
escapes `run_orchestration` -- propagates up through
`get_db_session`'s own `except` clause, which rolls the transaction
back and re-raises. Concretely: the conversation row, the user-message
row, and the assistant-message row are either all persisted together or
none of them are. This satisfies the architecture's failure strategy
(§22) without inventing a more elaborate unit-of-work -- an assistant
response is never persisted as if it were successful when orchestration
itself failed, and no orphaned user-only turn is ever left behind.
"""

import uuid
from typing import Dict, List

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.copilot_service.app.models.conversation import CopilotConversation
from backend.services.copilot_service.app.repositories.conversation_repository import CopilotConversationRepository
from backend.services.copilot_service.app.repositories.message_repository import CopilotMessageRepository
from backend.services.copilot_service.app.schemas.copilot import CopilotQueryRequest, CopilotQueryResponse
from backend.services.copilot_service.app.services.orchestrator.orchestrator_service import run_orchestration
from backend.shared.constants.enums.copilot import CopilotMessageRole


async def handle_persisted_query(
    request: CopilotQueryRequest, *, client: httpx.AsyncClient, request_id: str, session: AsyncSession
) -> CopilotQueryResponse:
    conversation_repository = CopilotConversationRepository(session)
    message_repository = CopilotMessageRepository(session)

    conversation_id, conversation = await _resolve_conversation(request, conversation_repository)

    history_rows = await message_repository.list_recent(conversation_id)
    history: List[Dict[str, str]] = [{"role": row.role.value, "content": row.content} for row in history_rows]

    await message_repository.append(
        conversation_id=conversation_id, role=CopilotMessageRole.USER, content=request.message
    )

    response = await run_orchestration(
        request,
        client=client,
        request_id=request_id,
        conversation_id=str(conversation_id),
        history=history,
    )

    await message_repository.append(
        conversation_id=conversation_id,
        role=CopilotMessageRole.ASSISTANT,
        content=response.answer,
        evidence_references=response.evidence_references or None,
    )
    await conversation_repository.touch_last_message_at(conversation)

    return response


async def _resolve_conversation(
    request: CopilotQueryRequest, conversation_repository: CopilotConversationRepository
) -> tuple[uuid.UUID, CopilotConversation]:
    """
    Mint-or-reuse conversation identity (COPILOT-002, unchanged from
    Batch 1's external contract: absent `conversation_id` -> a new one is
    generated; a supplied `conversation_id` is reused).

    No ownership/auth model exists in this prototype (Phase 13 boundary,
    architecture §28), and `conversation_id` is an opaque continuity
    token the client only ever received from a prior Copilot response.
    A *supplied* id that has no matching row (e.g. this is genuinely its
    first-ever turn, or a caller-fabricated value) is therefore treated
    as the start of a new conversation under that exact id -- never
    silently substituted with a different, server-generated id, and
    never rejected outright, since no frozen behavior governs this case
    and there is no user identity to validate it against.
    """
    if request.conversation_id is not None:
        conversation_id = uuid.UUID(request.conversation_id)
        conversation = await conversation_repository.get(conversation_id)
        if conversation is None:
            conversation = await conversation_repository.create(
                conversation_id, workspace_context=request.workspace_context
            )
        return conversation_id, conversation

    conversation_id = uuid.uuid4()
    conversation = await conversation_repository.create(conversation_id, workspace_context=request.workspace_context)
    return conversation_id, conversation
