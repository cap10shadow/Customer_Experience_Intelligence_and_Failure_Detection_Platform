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
from typing import Dict, List, Optional

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.copilot_service.app.models.conversation import CopilotConversation
from backend.services.copilot_service.app.repositories.conversation_repository import CopilotConversationRepository
from backend.services.copilot_service.app.repositories.message_repository import CopilotMessageRepository
from backend.services.copilot_service.app.schemas.copilot import CopilotQueryRequest, CopilotQueryResponse
from backend.services.copilot_service.app.services.orchestrator.llm_provider import LLMProvider
from backend.services.copilot_service.app.services.orchestrator.orchestrator_service import run_orchestration
from backend.shared.constants.enums.copilot import CopilotMessageRole


async def handle_persisted_query(
    request: CopilotQueryRequest,
    *,
    client: httpx.AsyncClient,
    request_id: str,
    session: AsyncSession,
    actor_id: Optional[uuid.UUID],
    llm_provider: Optional[LLMProvider] = None,
) -> CopilotQueryResponse:
    """
    Phase 12 Batch 6: `llm_provider` is an optional, additive override
    (default `None` -> unchanged existing behavior) threaded straight
    through to `run_orchestration`, for the same reason documented on
    that function -- lets `app/evaluation/runner.py` exercise this exact
    real, persisted conversation path with a deterministic provider. The
    real API route (`api/copilot.py` -> `copilot_query_service.py`)
    never passes this; production behavior is unchanged.

    Phase 13 Batch 6 (AD-4, §16/§17): `actor_id` is the Gateway-attested
    principal (`X-Authenticated-User-Id`), resolved by `api/copilot.py`
    from the trusted internal-auth header -- never a client-supplied
    field. Required (not optional) to reach `_resolve_conversation`,
    which raises `401` if it is `None` -- see that function's docstring
    for the full ownership contract.
    """
    conversation_repository = CopilotConversationRepository(session)
    message_repository = CopilotMessageRepository(session)

    conversation_id, conversation = await _resolve_conversation(request, conversation_repository, actor_id=actor_id)

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
        llm_provider=llm_provider,
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
    request: CopilotQueryRequest,
    conversation_repository: CopilotConversationRepository,
    *,
    actor_id: Optional[uuid.UUID],
) -> tuple[uuid.UUID, CopilotConversation]:
    """
    Mint-or-reuse conversation identity (COPILOT-002, Batch 1's external
    contract, unchanged: absent `conversation_id` -> a new one is
    generated; a supplied `conversation_id` with no matching row is
    treated as the start of a new conversation under that exact id --
    never silently substituted, never rejected outright).

    Phase 13 Batch 6 (AD-4, §16/§17) layers ownership on top of that
    unchanged mint-or-reuse behavior:

    - `actor_id` is the Gateway-attested principal, trustworthy only
      because it already passed the internal-secret boundary
      (`require_internal_secret`, Batch 4) before reaching here. `None`
      means no trusted identity was resolvable for this request -- this
      is an authentication failure, not an authorization one, so it
      raises `401` immediately, before any conversation is read or
      created. AD-4 is unconditional here ("every conversation created
      after Phase 13 ships must have one"): there is no carve-out for
      minting an owner-less conversation, ever.
    - Creating a conversation (new id, or a supplied id with no
      matching row) always sets `owner_id=actor_id`.
    - Continuing an existing conversation requires `conversation.owner_id
      == actor_id` exactly. A `None` `owner_id` (a pre-Phase-13 orphaned
      row) never matches any `actor_id`, by construction -- per §17,
      such rows are "treated as inaccessible until a future decision
      addresses them, not silently granted to the first caller who
      guesses the UUID." A mismatched real owner is rejected the same
      way. Both raise `403` -- a real, resolved identity was present,
      it simply isn't this conversation's owner (as opposed to the
      `401` above, where no identity was present at all).
    """
    if actor_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authenticated principal.")

    if request.conversation_id is not None:
        conversation_id = uuid.UUID(request.conversation_id)
        conversation = await conversation_repository.get(conversation_id)
        if conversation is None:
            conversation = await conversation_repository.create(
                conversation_id, workspace_context=request.workspace_context, owner_id=actor_id
            )
            return conversation_id, conversation
        if conversation.owner_id != actor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this conversation."
            )
        return conversation_id, conversation

    conversation_id = uuid.uuid4()
    conversation = await conversation_repository.create(
        conversation_id, workspace_context=request.workspace_context, owner_id=actor_id
    )
    return conversation_id, conversation


async def delete_conversation(
    conversation_id: uuid.UUID, *, actor_id: Optional[uuid.UUID], conversation_repository: CopilotConversationRepository
) -> None:
    """
    Phase 13 Batch 6 (AD-4, §17/§18): `DELETE /api/v1/copilot/conversations/{id}`,
    owner-only, no admin override (AD-4 is explicit: "no admin-override
    route is introduced"). Same `401`-vs-`403` split as
    `_resolve_conversation`: no `actor_id` at all is an authentication
    failure; a real `actor_id` that isn't this conversation's owner (or
    a conversation with a `None` owner_id -- pre-Phase-13/orphaned,
    inaccessible to everyone per §17) is an authorization failure. A
    conversation that genuinely does not exist is `404` -- distinct from
    both, and checked only after confirming a real principal is present.
    """
    if actor_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authenticated principal.")

    conversation = await conversation_repository.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    if conversation.owner_id != actor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this conversation."
        )

    await conversation_repository.delete(conversation)
