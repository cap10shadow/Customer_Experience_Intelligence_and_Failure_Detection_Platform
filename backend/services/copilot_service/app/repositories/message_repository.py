import uuid
from typing import List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.copilot_service.app.models.message import CopilotMessage
from backend.services.copilot_service.app.schemas.copilot import EvidenceReference
from backend.shared.constants.enums.copilot import CopilotMessageRole

# Bounded conversation-history window read back into the prompt (§17 of
# the Batch 4 implementation prompt: "load only the bounded history
# required by the frozen design"; §19 of the architecture requires a
# bounded "conversation context size" to exist, without freezing an
# exact number). 20 messages (10 user/assistant turns) is this batch's
# own implementation-time configuration decision, sized consistently
# with `MAX_EVIDENCE_ITEMS` in `orchestrator/graph.py`.
MAX_HISTORY_MESSAGES = 20


class CopilotMessageRepository:
    """
    CopilotMessage Repository

    Ownership:
    Owned by the Copilot Service context (COPILOT-002, architecture §17).

    Operational Purpose:
    Responsible strictly for database persistence and retrieval of
    CopilotMessage rows. Contains no orchestration/LLM logic -- only
    data access.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(
        self,
        *,
        conversation_id: uuid.UUID,
        role: CopilotMessageRole,
        content: str,
        evidence_references: Optional[List[EvidenceReference]] = None,
    ) -> CopilotMessage:
        message = CopilotMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            evidence_references=(
                [reference.model_dump(mode="json") for reference in evidence_references]
                if evidence_references
                else None
            ),
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def list_recent(
        self, conversation_id: uuid.UUID, *, limit: int = MAX_HISTORY_MESSAGES
    ) -> Sequence[CopilotMessage]:
        """
        Returns up to `limit` most recent messages for the conversation,
        in deterministic chronological (oldest-first) order -- ordering
        by the database-assigned monotonic `sequence` column, never
        accidental insertion order (§9 of the Batch 4 implementation
        prompt).
        """
        stmt = (
            select(CopilotMessage)
            .where(CopilotMessage.conversation_id == conversation_id)
            .order_by(CopilotMessage.sequence.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        most_recent_first = result.scalars().all()
        return list(reversed(most_recent_first))
