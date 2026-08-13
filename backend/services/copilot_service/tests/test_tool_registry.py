"""
Tests for the Phase 12 Batch 2 tool registry -- explicit registration,
read-only enforcement, and the exact 7-tool set the frozen architecture's
Tool Contract Matrix (§13) approves.
"""

import httpx
import pytest
from pydantic import BaseModel

from backend.services.copilot_service.app.services import tools_bootstrap  # noqa: F401  (registers all 7 tools)
from backend.services.copilot_service.app.services.tool_registry import (
    ToolDefinition,
    UnknownToolError,
    call_tool,
    get_tool,
    list_tools,
    register_tool,
)

EXPECTED_TOOL_NAMES = {
    "recommendation",
    "recommendation_decision_status",
    "root_cause",
    "business_impact",
    "investigation",
    "analytics_trends",
    "administration_configuration",
}


def test_exactly_the_seven_approved_tools_are_registered():
    assert set(list_tools().keys()) == EXPECTED_TOOL_NAMES


def test_every_registered_tool_is_read_only():
    for definition in list_tools().values():
        assert definition.read_only is True


def test_get_tool_returns_the_matching_definition():
    definition = get_tool("recommendation")
    assert definition.name == "recommendation"


def test_get_unknown_tool_raises_cleanly():
    with pytest.raises(UnknownToolError):
        get_tool("delete_everything")


def test_registering_a_duplicate_name_is_rejected():
    class _Input(BaseModel):
        pass

    class _Output(BaseModel):
        pass

    async def _executor(client, tool_input):
        return _Output()

    with pytest.raises(ValueError):
        register_tool(
            ToolDefinition(
                name="recommendation",  # already registered
                description="duplicate",
                input_model=_Input,
                output_model=_Output,
                executor=_executor,
            )
        )


def test_a_mutation_tool_definition_is_rejected_structurally():
    class _Input(BaseModel):
        pass

    class _Output(BaseModel):
        pass

    async def _executor(client, tool_input):
        return _Output()

    with pytest.raises(ValueError):
        register_tool(
            ToolDefinition(
                name="delete_recommendation",
                description="would mutate",
                input_model=_Input,
                output_model=_Output,
                executor=_executor,
                read_only=False,
            )
        )
    # And it must never have made it into the registry.
    with pytest.raises(UnknownToolError):
        get_tool("delete_recommendation")


def test_no_downstream_client_module_exposes_a_mutating_http_verb():
    """
    Structural enforcement, not just a naming convention: copilot_service's
    own downstream client module must expose no post/patch/put/delete
    helper at all (Phase 12 architecture §12).
    """
    from backend.services.copilot_service.app.core import downstream

    exported = {name for name in dir(downstream) if not name.startswith("_")}
    assert "get_json" in exported
    assert not any(name in exported for name in ("post_json", "patch_json", "put_json", "delete_json"))


@pytest.mark.anyio
async def test_call_tool_validates_input_against_the_tool_s_own_model():
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(404)))
    result = await call_tool("recommendation_decision_status", client, {"recommendation_id": "abc-123"})
    assert result.found is False


@pytest.fixture
def anyio_backend():
    return "asyncio"
