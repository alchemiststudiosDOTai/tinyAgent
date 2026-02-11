"""Unit tests for OpenRouter provider helpers."""

from __future__ import annotations

import pytest

from tinyagent.agent_types import Model
from tinyagent.openrouter_provider import (
    OPENROUTER_API_URL,
    OpenRouterModel,
    _resolve_openrouter_api_url,
)


def test_resolve_openrouter_api_url_defaults_for_generic_model() -> None:
    model = Model(provider="openrouter", id="openai/gpt-4o", api="openrouter")
    assert _resolve_openrouter_api_url(model) == OPENROUTER_API_URL


def test_resolve_openrouter_api_url_uses_override_from_model() -> None:
    model = OpenRouterModel(
        id="gpt-4o-mini",
        base_url="https://api.openai.com/v1/chat/completions",
    )
    assert _resolve_openrouter_api_url(model) == "https://api.openai.com/v1/chat/completions"


def test_resolve_openrouter_api_url_trims_whitespace() -> None:
    model = OpenRouterModel(base_url="  http://localhost:11434/v1/chat/completions  ")
    assert _resolve_openrouter_api_url(model) == "http://localhost:11434/v1/chat/completions"


def test_resolve_openrouter_api_url_rejects_blank_string() -> None:
    model = OpenRouterModel(base_url="   ")
    with pytest.raises(ValueError, match="base_url"):
        _resolve_openrouter_api_url(model)
