from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Type

import httpx
from pydantic import BaseModel

# Phase 12 Batch 2 -- a simple, explicit, static tool registry (Phase 12
# architecture §9/§10). No dynamic loading, no plugin discovery, no
# runtime code execution: every tool is registered once, here, by name.
# `read_only` is a fixed literal on every registration below -- there is
# no code path that can register a tool with `read_only=False`, and the
# only HTTP verb available to any executor is `core/downstream.py`'s
# `get_json` (no POST/PUT/PATCH/DELETE helper exists in this service at
# all), so the read-only invariant is structural, not just declared.


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_model: Type[BaseModel]
    output_model: Type[BaseModel]
    executor: Callable[[httpx.AsyncClient, BaseModel], Awaitable[BaseModel]]
    read_only: bool = True


class UnknownToolError(Exception):
    """Raised by `get_tool` for a name that was never registered -- never a fabricated/guessed tool."""


_REGISTRY: Dict[str, ToolDefinition] = {}


def register_tool(definition: ToolDefinition) -> None:
    if not definition.read_only:
        # Structural backstop: even a future edit that tried to pass
        # `read_only=False` is rejected here, not merely documented.
        raise ValueError(f"Tool '{definition.name}' must be read-only.")
    if definition.name in _REGISTRY:
        raise ValueError(f"Tool '{definition.name}' is already registered.")
    _REGISTRY[definition.name] = definition


def get_tool(name: str) -> ToolDefinition:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise UnknownToolError(f"No tool named '{name}' is registered.") from exc


def list_tools() -> Dict[str, ToolDefinition]:
    """Read-only snapshot of the registry -- callers cannot mutate the live registry through this."""
    return dict(_REGISTRY)


async def call_tool(name: str, client: httpx.AsyncClient, tool_input: Any) -> BaseModel:
    """
    The one execution path every tool call goes through (used directly
    by tests in Batch 2; will be the same path Batch 3's orchestrator
    calls). Validates `tool_input` against the tool's own declared input
    model before invoking its executor.
    """
    definition = get_tool(name)
    validated_input = (
        tool_input if isinstance(tool_input, definition.input_model) else definition.input_model.model_validate(tool_input)
    )
    return await definition.executor(client, validated_input)
