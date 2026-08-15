import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.copilot_service.app.models.conversation import CopilotConversation
from backend.services.copilot_service.app.schemas.copilot import WorkspaceContext


class CopilotConversationRepository:
    """
    CopilotConversation Repository

    Ownership:
    Owned by the Copilot Service context (COPILOT-002, architecture §17).

    Operational Purpose:
    Responsible strictly for database persistence and retrieval of
    CopilotConversation rows. Contains no orchestration/LLM logic --
    only data access, matching the established convention (see
    `BusinessImpactRepository`, `RootCauseRepository`).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, conversation_id: uuid.UUID) -> Optional[CopilotConversation]:
        stmt = select(CopilotConversation).where(CopilotConversation.conversation_id == conversation_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        conversation_id: uuid.UUID,
        *,
        workspace_context: Optional[WorkspaceContext],
        owner_id: Optional[uuid.UUID] = None,
    ) -> CopilotConversation:
        """
        Creates a new conversation row, snapshotting the launch context
        (§4.1) exactly once. `filters`/`time_range` are deliberately not
        persisted -- §17's conceptual `copilot_conversations` schema
        names only `workspace`/`incidentId`/`recommendationId` as the
        stored context fields.

        `owner_id` (Phase 13 Batch 6, AD-4): the Gateway-attested
        principal, supplied by the caller -- never resolved here. This
        repository method itself enforces nothing about it (it accepts
        `None`, matching the column's nullable-at-the-database-level
        design for pre-Phase-13 rows); the "every new conversation must
        have a real owner" invariant is `_resolve_conversation`'s own
        application-layer responsibility, not this repository's.
        """
        conversation = CopilotConversation(
            conversation_id=conversation_id,
            workspace=workspace_context.workspace if workspace_context else None,
            incident_id=workspace_context.incident_id if workspace_context else None,
            recommendation_id=workspace_context.recommendation_id if workspace_context else None,
            owner_id=owner_id,
        )
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def touch_last_message_at(self, conversation: CopilotConversation) -> None:
        """
        Explicitly sets `last_message_at` in application code -- the same
        `onupdate=func.now()` MissingGreenlet hazard documented on
        `RootCause.updated_at` applies here, so this is set directly
        rather than relying on a computed column.
        """
        conversation.last_message_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def delete(self, conversation: CopilotConversation) -> None:
        """
        Hard-deletes one conversation row (Phase 13 Batch 6, AD-4:
        `DELETE /api/v1/copilot/conversations/{id}`, owner-only). Every
        `copilot_messages` row for this conversation cascades with it --
        `CopilotMessage.conversation_id`'s own `ondelete="CASCADE"` FK
        (a real, same-service ORM FK, see that model's docstring) is the
        established mechanism, not application-code cleanup here.
        Ownership verification is this method's caller's responsibility
        (`conversation_service.delete_conversation`), not this
        repository's -- this method performs the deletion unconditionally
        once called.
        """
        await self.session.delete(conversation)
        await self.session.flush()
