"""Unit tests for alchemy provider helper behavior."""

from __future__ import annotations

import pytest

from tinyagent.agent_types import Model
from tinyagent.alchemy_provider import (
    DEFAULT_OPENAI_COMPAT_CHAT_COMPLETIONS_URL,
    OpenAICompatModel,
    _resolve_api_key,
    _resolve_base_url,
)


def test_resolve_base_url_defaults_for_generic_model() -> None:
    model = Model(provider="openrouter", id="openai/gpt-4o-mini", api="openrouter")
    assert _resolve_base_url(model) == DEFAULT_OPENAI_COMPAT_CHAT_COMPLETIONS_URL


def test_resolve_base_url_uses_model_override() -> None:
    model = OpenAICompatModel(base_url="https://api.openai.com/v1/chat/completions")
    assert _resolve_base_url(model) == "https://api.openai.com/v1/chat/completions"


def test_resolve_base_url_trims_whitespace() -> None:
    model = OpenAICompatModel(base_url="  https://llm.chutes.ai/v1/chat/completions  ")
    assert _resolve_base_url(model) == "https://llm.chutes.ai/v1/chat/completions"


def test_resolve_base_url_rejects_blank() -> None:
    model = OpenAICompatModel(base_url="   ")
    with pytest.raises(ValueError, match="base_url"):
        _resolve_base_url(model)


def test_resolve_api_key_prefers_explicit_option(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "env-openrouter")
    model = Model(provider="openrouter", id="x", api="openrouter")
    assert _resolve_api_key(model, {"api_key": "explicit"}) == "explicit"


def test_resolve_api_key_openrouter_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "env-openrouter")
    model = Model(provider="openrouter", id="x", api="openrouter")
    assert _resolve_api_key(model, {}) == "env-openrouter"


def test_resolve_api_key_openai_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai")
    model = Model(provider="openai", id="x", api="openai")
    assert _resolve_api_key(model, {}) == "env-openai"
