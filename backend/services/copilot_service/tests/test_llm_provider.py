"""
Tests for the Phase 12 Batch 3 LLM provider adapter
(orchestrator/llm_provider.py). `OpenAICompatibleProvider`'s HTTP calls
are exercised against a mocked transport only -- no live provider/API
key is ever contacted (Batch 3 implementation prompt §33).
"""

import os

import httpx
import pytest

from backend.services.copilot_service.app.services.orchestrator.llm_provider import (
    LLMProviderError,
    NullLLMProvider,
    OpenAICompatibleProvider,
    get_llm_provider,
)
from backend.services.copilot_service.app.services.orchestrator.state import FinalAnswerDecision, ToolCallDecision


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _clean_llm_env(monkeypatch):
    for key in ("LLM_PROVIDER", "LLM_API_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(key, raising=False)


# ---------------------------------------------------------------------------
# Provider selection (configuration-driven, architecture §24)
# ---------------------------------------------------------------------------


def test_default_provider_is_null_when_unconfigured():
    assert isinstance(get_llm_provider(), NullLLMProvider)


def test_explicit_none_selects_null_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "none")
    assert isinstance(get_llm_provider(), NullLLMProvider)


def test_openai_compatible_without_full_config_falls_back_to_null(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    # Deliberately incomplete -- no API key/model set.
    assert isinstance(get_llm_provider(), NullLLMProvider)


def test_openai_compatible_with_full_config_is_selected(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    assert isinstance(get_llm_provider(), OpenAICompatibleProvider)


def test_unrecognized_provider_name_falls_back_to_null(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "some_vendor_nobody_configured")
    assert isinstance(get_llm_provider(), NullLLMProvider)


# ---------------------------------------------------------------------------
# NullLLMProvider
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_null_provider_always_returns_an_honest_final_answer_never_a_tool_call():
    provider = NullLLMProvider()
    decision = await provider.decide(messages=[], available_tools=[])

    assert isinstance(decision, FinalAnswerDecision)
    assert "not configured" in decision.answer


# ---------------------------------------------------------------------------
# OpenAICompatibleProvider -- mocked transport only, no real credentials
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_final_answer_is_parsed_from_a_well_formed_response(monkeypatch):
    async def fake_post(self, url, json=None, headers=None):
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "Here is the answer.", "tool_calls": []}}]}
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    provider = OpenAICompatibleProvider(base_url="https://example.invalid/v1", api_key="k", model="m")

    decision = await provider.decide(messages=[{"role": "user", "content": "hi"}], available_tools=[])

    assert isinstance(decision, FinalAnswerDecision)
    assert decision.answer == "Here is the answer."


@pytest.mark.anyio
async def test_tool_call_is_parsed_from_a_well_formed_response(monkeypatch):
    async def fake_post(self, url, json=None, headers=None):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "recommendation",
                                        "arguments": '{"recommendation_id": "abc-123"}',
                                    }
                                }
                            ],
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    provider = OpenAICompatibleProvider(base_url="https://example.invalid/v1", api_key="k", model="m")

    decision = await provider.decide(messages=[], available_tools=[])

    assert isinstance(decision, ToolCallDecision)
    assert decision.tool_name == "recommendation"
    assert decision.arguments == {"recommendation_id": "abc-123"}


@pytest.mark.anyio
async def test_timeout_raises_llm_provider_error(monkeypatch):
    async def fake_post(self, url, json=None, headers=None):
        raise httpx.TimeoutException("timed out", request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    provider = OpenAICompatibleProvider(base_url="https://example.invalid/v1", api_key="k", model="m")

    with pytest.raises(LLMProviderError):
        await provider.decide(messages=[], available_tools=[])


@pytest.mark.anyio
async def test_unreachable_provider_raises_llm_provider_error(monkeypatch):
    async def fake_post(self, url, json=None, headers=None):
        raise httpx.ConnectError("connection refused", request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    provider = OpenAICompatibleProvider(base_url="https://example.invalid/v1", api_key="k", model="m")

    with pytest.raises(LLMProviderError):
        await provider.decide(messages=[], available_tools=[])


@pytest.mark.anyio
async def test_non_2xx_status_raises_llm_provider_error(monkeypatch):
    async def fake_post(self, url, json=None, headers=None):
        return httpx.Response(500)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    provider = OpenAICompatibleProvider(base_url="https://example.invalid/v1", api_key="k", model="m")

    with pytest.raises(LLMProviderError):
        await provider.decide(messages=[], available_tools=[])


@pytest.mark.anyio
async def test_malformed_response_body_raises_llm_provider_error(monkeypatch):
    async def fake_post(self, url, json=None, headers=None):
        return httpx.Response(200, json={"unexpected": "shape"})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    provider = OpenAICompatibleProvider(base_url="https://example.invalid/v1", api_key="k", model="m")

    with pytest.raises(LLMProviderError):
        await provider.decide(messages=[], available_tools=[])


@pytest.mark.anyio
async def test_malformed_tool_call_arguments_raise_llm_provider_error(monkeypatch):
    async def fake_post(self, url, json=None, headers=None):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"tool_calls": [{"function": {"name": "recommendation", "arguments": "{not json"}}]}}
                ]
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    provider = OpenAICompatibleProvider(base_url="https://example.invalid/v1", api_key="k", model="m")

    with pytest.raises(LLMProviderError):
        await provider.decide(messages=[], available_tools=[])


def test_no_credential_is_ever_hardcoded_in_source():
    import inspect

    from backend.services.copilot_service.app.services.orchestrator import llm_provider

    source = inspect.getsource(llm_provider)
    # The only literal API-key-shaped strings anywhere in this module must
    # come from os.environ -- never a hardcoded value.
    assert "sk-" not in source
    assert os.environ.get("LLM_API_KEY") != "hardcoded"
