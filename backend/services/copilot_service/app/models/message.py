import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Identity, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.constants.enums.copilot import CopilotMessageRole
from backend.shared.database.base import Base


class CopilotMessage(Base):
    """
    Copilot Message Entity

    Ownership:
    Owned by `copilot_service` (COPILOT-002, architecture §17).

    Operational Purpose:
    One row per persisted user or assistant turn in a Copilot
    conversation. `evidence_references` stores only the bounded §14.1
    evidence shape already returned to the frontend on an assistant
    turn (`evidenceId`/`sourceType`/`sourceId`/`authority`/`timestamp`)
    -- never raw tool payloads, prompts, or provider responses (§21/§22
    of the Batch 4 implementation prompt; §24.2 Data Minimization).

    Architectural Boundaries:
    - `conversation_id` is a real ORM `ForeignKey` to
      `copilot_conversations.conversation_id`: both tables are owned by
      this same service, so none of DATA-002's cross-service coupling
      risk applies -- the same established intra-service pattern as
      `AnomalyHistory.active_anomaly_id` -> `active_anomalies.id`.
    - `sequence` is a database-assigned, strictly monotonic identity
      column -- purely an ordering mechanism, not a domain field. It
      exists because `created_at` alone cannot guarantee deterministic
      ordering when two messages in the same turn (user append, then
      assistant append after orchestration) could in principle share a
      timestamp at the column's storage resolution.
    - Only a user or assistant message is ever persisted (`role`) --
      there is no "system"/"tool" role stored here. Internal
      orchestration state (tool calls, prompt layers) is not persisted
      by this batch, per the Batch 4 implementation prompt §7.
    """

    __tablename__ = "copilot_messages"

    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("copilot_conversations.conversation_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, Identity(), nullable=False, unique=True)

    role: Mapped[CopilotMessageRole] = mapped_column(Enum(CopilotMessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_references: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
