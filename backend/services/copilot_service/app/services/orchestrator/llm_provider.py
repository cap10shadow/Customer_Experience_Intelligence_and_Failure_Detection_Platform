"""
Phase 12 Batch 3 -- LLM provider adapter (architecture §24).

The frozen architecture is explicit that no provider/model/credential is
decided by the document itself -- verified directly against the
repository before this file was written: zero LLM dependencies, zero LLM
environment variables, no existing `copilot_service` LLM configuration
anywhere. This module therefore implements the adapter *boundary* plus:

- `NullLLMProvider`: the honest default when no provider is configured
  (`LLM_PROVIDER` unset/`"none"`) -- Copilot remains fully optional
  (§22): it never fabricates an answer, it says plainly that no language
  model is configured, and it never calls a tool it has no real
  justification for calling.
- `OpenAICompatibleProvider`: one concrete, genuinely usable
  implementation against the OpenAI-compatible chat-completions wire
  format (the de facto standard many providers and self-hosted runtimes
  implement) -- not a vendor SDK, just `httpx` (already a dependency),
  configured entirely via environment variables. Never installed or
  exercised by default; opt-in only when `LLM_PROVIDER=openai_compatible`
  and its URL/key/model are actually configured.

Orchestrator code depends only on the `LLMProvider` Protocol below --
never on a concrete provider -- satisfying "the orchestrator must not be
tightly coupled to one provider's API."
"""

import json
import os
from typing import Any, Dict, List, Protocol

import httpx

from backend.services.copilot_service.app.services.orchestrator.state import Decision, FinalAnswerDecision, ToolCallDecision

_REQUEST_TIMEOUT_SECONDS = 20.0


class LLMProviderError(Exception):
    """Raised by a provider on genuine failure (timeout, unreachable, malformed response). Never raised for 'no provider configured'."""


class LLMProvider(Protocol):
    async def decide(
        self,
        *,
        messages: List[Dict[str, str]],
        available_tools: List[Dict[str, Any]],
    ) -> Decision: ...


class NullLLMProvider:
    """
    The default, dependency-free provider. Always returns one honest
    final answer, never calls a tool -- there is no language
    understanding available to justify selecting one (Phase 12
    architecture §21: never invent a finding, and selecting a tool
    without genuine intent interpretation would itself be a form of
    fabrication).
    """

    async def decide(
        self, *, messages: List[Dict[str, str]], available_tools: List[Dict[str, Any]]
    ) -> Decision:
        return FinalAnswerDecision(
            answer="Copilot's language model is not configured in this environment, so this request cannot be interpreted.",
            limitations=["No LLM provider is configured (LLM_PROVIDER is unset); no tool was called."],
        )


class OpenAICompatibleProvider:
    """
    Calls a configurable OpenAI-compatible `/chat/completions` endpoint
    with function/tool-calling. Configuration only -- no hardcoded
    endpoint, key, or model (architecture §24: "no credentials are
    committed at any point; secrets are environment-injected the same
    way POSTGRES_PASSWORD/every other credential in this repository
    already is").
    """

    def __init__(self, *, base_url: str, api_key: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model

    async def decide(
        self, *, messages: List[Dict[str, str]], available_tools: List[Dict[str, Any]]
    ) -> Decision:
        tool_specs = [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                },
            }
            for tool in available_tools
        ]
        payload = {
            "model": self._model,
            "messages": messages,
            "tools": tool_specs,
            "tool_choice": "auto",
        }
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(f"{self._base_url}/chat/completions", json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise LLMProviderError("The language model provider timed out.") from exc
        except httpx.RequestError as exc:
            raise LLMProviderError("The language model provider could not be reached.") from exc

        if response.status_code >= 400:
            raise LLMProviderError(f"The language model provider returned status {response.status_code}.")

        try:
            body = response.json()
            choice = body["choices"][0]["message"]
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMProviderError("The language model provider returned a malformed response.") from exc

        tool_calls = choice.get("tool_calls") or []
        if tool_calls:
            call = tool_calls[0]
            try:
                arguments = json.loads(call["function"]["arguments"] or "{}")
            except (KeyError, ValueError) as exc:
                raise LLMProviderError("The language model provider returned a malformed tool call.") from exc
            return ToolCallDecision(tool_name=call["function"]["name"], arguments=arguments)

        content = choice.get("content") or ""
        return FinalAnswerDecision(answer=content)


def get_llm_provider() -> LLMProvider:
    """
    Configuration-driven provider selection (architecture §24). Defaults
    to `NullLLMProvider` -- the honest, always-available fallback -- when
    `LLM_PROVIDER` is unset, matching the verified repository reality
    that no provider is configured today.
    """
    provider_name = os.environ.get("LLM_PROVIDER", "none").strip().lower()
    if provider_name in ("", "none"):
        return NullLLMProvider()
    if provider_name == "openai_compatible":
        base_url = os.environ.get("LLM_API_BASE_URL")
        api_key = os.environ.get("LLM_API_KEY")
        model = os.environ.get("LLM_MODEL")
        if not base_url or not api_key or not model:
            # Misconfiguration must degrade honestly, never crash the
            # request path or silently fall back to fabricated behavior.
            return NullLLMProvider()
        return OpenAICompatibleProvider(base_url=base_url, api_key=api_key, model=model)
    return NullLLMProvider()
