from backend.shared.constants.enums.base import BaseStringEnum


class CopilotMessageRole(BaseStringEnum):
    """
    Role of one persisted Copilot conversation turn (architecture §17,
    `docs/architecture/phase-12/PHASE_12_ARCHITECTURE.md`). Only the two
    conversational roles are ever persisted -- internal orchestration
    state (tool calls, system/tool prompt layers) is never stored as a
    message row.
    """

    USER = "user"
    ASSISTANT = "assistant"
