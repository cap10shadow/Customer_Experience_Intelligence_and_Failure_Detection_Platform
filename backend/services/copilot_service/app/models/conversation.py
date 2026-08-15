import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.database.base import Base


class CopilotConversation(Base):
    """
    Copilot Conversation Entity

    Ownership:
    Owned by `copilot_service` (COPILOT-002, architecture §17).

    Operational Purpose:
    One row per Copilot conversation thread. Exists only to give
    follow-up questions continuity within a session/thread (§17 --
    "conversation history exists only for follow-up-question continuity
    within a session/thread"). It is never organizational memory: never
    read by another user's conversation, never aggregated into a
    knowledge base, and never referenced by any domain service.

    Architectural Boundaries:
    - `workspace`/`incident_id`/`recommendation_id` are a one-time
      snapshot of the Copilot launch context (§4.1), captured only when
      the conversation is first created. They are never rewritten by a
      later turn, and never feed back into any workspace Context --
      Copilot launch context is input, never authority, over workspace
      state (§4.1's explicit invariant).
    - `owner_id` (Phase 13 Batch 6, AD-4): nullable UUID, no ORM
      `ForeignKey` (cross-service reference to gateway_service's
      `users.id`; referential integrity is enforced by a raw Alembic FK
      constraint only, per DATA-001/DATA-002 -- see the migration for
      the full rationale, mirroring `RecommendationModel.decided_by`'s
      established precedent). Nullable only to preserve pre-Phase-13
      rows -- every conversation created from this point forward is
      required to carry a real owner, enforced at the application layer
      (`conversation_service._resolve_conversation`), never at the
      database level. Populated exclusively from the Gateway-attested
      principal header, never from client-supplied request data.
    - No retention/TTL/expiry field exists: §17 -- "No automatic expiry
      in the prototype", consistent with every other entity in this
      platform.
    """

    __tablename__ = "copilot_conversations"

    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    workspace: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    incident_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    recommendation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Deliberately no `onupdate=func.now()` -- same MissingGreenlet hazard
    # documented on RootCause.updated_at/BusinessImpactAssessmentEntity.
    # updated_at. Set explicitly, in application code, by
    # CopilotConversationRepository each time a message is appended.
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
