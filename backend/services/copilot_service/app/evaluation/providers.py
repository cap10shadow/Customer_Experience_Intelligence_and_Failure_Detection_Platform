"""
`ScriptedLLMProvider` -- a deterministic stand-in implementing the exact
same `LLMProvider` Protocol (`orchestrator/llm_provider.py`) every real
provider does. It is not a second orchestration path: the evaluation
runner passes it into the real, unmodified `run_orchestration` ->
`build_graph` -> graph execution -> `synthesize_response` pipeline, so
every safety/no-fabrication/read-only guarantee those modules already
enforce (Batch 3) applies exactly as it would to a real model's output.

This is the same pattern `backend/services/copilot_service/tests/
test_orchestrator_graph.py`'s own `FakeLLMProvider` already established
for Batch 3's tests -- reused here as a first-class evaluation-harness
component instead of a test-local fixture, since deterministic,
reproducible tool-selection/conflict-disclosure scenarios are
unreachable with `NullLLMProvider` (never calls a tool) and this
environment has no real LLM credentials (§9 of the Batch 6
implementation prompt).
"""

from typing import Any, Dict, List

from backend.services.copilot_service.app.evaluation.dataset import ScriptedFinalAnswerSpec, ScriptedToolCallSpec
from backend.services.copilot_service.app.services.orchestrator.state import Decision, FinalAnswerDecision, ToolCallDecision


class ScriptedProviderExhaustedError(Exception):
    """Raised if the graph asks for more decisions than the case scripted -- a case-authoring bug, never silently papered over."""


class ScriptedLLMProvider:
    """Replays a fixed, ordered sequence of decisions -- ignores `messages`/`available_tools` entirely, exactly like `FakeLLMProvider`."""

    def __init__(self, decisions: List[ScriptedToolCallSpec | ScriptedFinalAnswerSpec]) -> None:
        self._decisions = list(decisions)
        self._index = 0

    async def decide(self, *, messages: List[Dict[str, str]], available_tools: List[Dict[str, Any]]) -> Decision:
        if self._index >= len(self._decisions):
            raise ScriptedProviderExhaustedError(
                f"ScriptedLLMProvider ran out of scripted decisions after {self._index} call(s)."
            )
        spec = self._decisions[self._index]
        self._index += 1

        if isinstance(spec, ScriptedToolCallSpec):
            return ToolCallDecision(tool_name=spec.tool_name, arguments=dict(spec.arguments))

        return FinalAnswerDecision(
            answer=spec.answer,
            key_findings=list(spec.key_findings),
            evidence_ids=list(spec.evidence_ids),
            visualization_hint=spec.visualization_hint,
            limitations=list(spec.limitations),
            conflicts=list(spec.conflicts),
        )
