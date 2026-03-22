"""Unit tests for alchemy provider helper behavior."""

from __future__ import annotations

from typing import cast

import pytest

from tinyagent.agent_types import (
    Context,
    Message,
    Model,
    SimpleStreamOptions,
    TextContent,
    UserMessage,
)
from tinyagent.alchemy_provider import (
    DEFAULT_OPENAI_COMPAT_CHAT_COMPLETIONS_URL,
    OpenAICompatModel,
    _get_alchemy_module,
    _resolve_api_key,
    _resolve_base_url,
    _resolve_model_api,
    stream_alchemy_openai_completions,
)


def test_resolve_base_url_defaults_for_generic_model() -> None:
    model = Model(provider="openai", id="gpt-4o-mini", api="openai")
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


def test_resolve_model_api_maps_openai_alias_to_openai_completions() -> None:
    model = Model(provider="openai", id="x", api="openai")
    assert _resolve_model_api(model, "openai") == "openai-completions"


def test_resolve_model_api_infers_minimax_completions_from_provider() -> None:
    model = Model(provider="minimax", id="MiniMax-M2.5", api="")
    assert _resolve_model_api(model, "minimax") == "minimax-completions"


def test_resolve_model_api_explicit_api_overrides_provider_inference() -> None:
    model = Model(provider="minimax", id="MiniMax-M2.5", api="openai-completions")
    assert _resolve_model_api(model, "minimax") == "openai-completions"


def test_resolve_api_key_prefers_explicit_option(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai")
    model = Model(provider="openai", id="x", api="openai")
    assert _resolve_api_key(model, SimpleStreamOptions(api_key="explicit")) == "explicit"


def test_resolve_api_key_openai_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai")
    model = Model(provider="openai", id="x", api="openai")
    assert _resolve_api_key(model, SimpleStreamOptions()) == "env-openai"


def test_resolve_api_key_openrouter_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "env-openrouter")
    model = Model(provider="openrouter", id="x", api="openai-completions")
    assert _resolve_api_key(model, SimpleStreamOptions()) == "env-openrouter"


def test_resolve_api_key_minimax_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MINIMAX_API_KEY", "env-minimax")
    model = Model(provider="minimax", id="MiniMax-M2.5", api="minimax-completions")
    assert _resolve_api_key(model, SimpleStreamOptions()) == "env-minimax"


def test_resolve_api_key_minimax_cn_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MINIMAX_CN_API_KEY", "env-minimax-cn")
    model = Model(provider="minimax-cn", id="MiniMax-M2.5", api="minimax-completions")
    assert _resolve_api_key(model, SimpleStreamOptions()) == "env-minimax-cn"


def test_resolve_api_key_unknown_provider_returns_none() -> None:
    model = Model(provider="my-custom-provider", id="x", api="openai-completions")
    assert _resolve_api_key(model, SimpleStreamOptions()) is None


def test_get_alchemy_module_falls_back_to_top_level_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imported: list[str] = []
    fallback_module = _FakeAlchemyModule()

    def fake_import_module(name: str) -> object:
        imported.append(name)
        if name == "_alchemy":
            return fallback_module
        if name == "tinyagent._alchemy":
            raise ModuleNotFoundError(name)
        raise AssertionError(f"unexpected import: {name}")

    monkeypatch.setattr("tinyagent.alchemy_provider._ALCHEMY_MODULE", None)
    monkeypatch.setattr("tinyagent.alchemy_provider.importlib.import_module", fake_import_module)

    resolved = _get_alchemy_module()

    assert resolved is fallback_module
    assert imported == ["_alchemy"]


def test_get_alchemy_module_reports_original_import_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imported: list[str] = []

    def fake_import_module(name: str) -> object:
        imported.append(name)
        if name == "_alchemy":
            raise ModuleNotFoundError(name)
        if name == "tinyagent._alchemy":
            raise ImportError("invalid Mach-O image")
        raise AssertionError(f"unexpected import: {name}")

    monkeypatch.setattr("tinyagent.alchemy_provider._ALCHEMY_MODULE", None)
    monkeypatch.setattr("tinyagent.alchemy_provider.importlib.import_module", fake_import_module)

    with pytest.raises(RuntimeError, match="Import failures") as exc_info:
        _get_alchemy_module()

    assert imported == ["_alchemy", "tinyagent._alchemy"]
    assert "invalid Mach-O image" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, ImportError)


class _FakeHandle:
    def next_event(self) -> object | None:
        return None

    def result(self) -> object:
        return {
            "role": "assistant",
            "content": [{"type": "text", "text": "ok"}],
            "stop_reason": "complete",
            "usage": {
                "input": 0,
                "output": 0,
                "cache_read": 0,
                "cache_write": 0,
                "total_tokens": 0,
                "cost": {
                    "input": 0.0,
                    "output": 0.0,
                    "cache_read": 0.0,
                    "cache_write": 0.0,
                    "total": 0.0,
                },
            },
        }


class _FakeAlchemyModule:
    def openai_completions_stream(
        self,
        model: dict[str, object],
        context: dict[str, object],
        options: dict[str, object],
    ) -> _FakeHandle:
        del model, context, options
        return _FakeHandle()


async def test_stream_alchemy_rejects_message_without_model_dump(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("tinyagent.alchemy_provider._ALCHEMY_MODULE", _FakeAlchemyModule())

    bad_messages = [object()]
    context = Context(
        system_prompt="test",
        messages=cast(list[Message], bad_messages),
    )

    with pytest.raises(TypeError, match=r"context\.messages"):
        await stream_alchemy_openai_completions(
            Model(provider="openai", id="gpt-4o-mini", api="openai-completions"),
            context,
            SimpleStreamOptions(),
        )


async def test_stream_alchemy_rejects_model_dump_returning_non_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BadDump:
        def model_dump(self, *, exclude_none: bool = True) -> list[object]:
            del exclude_none
            return []

    monkeypatch.setattr("tinyagent.alchemy_provider._ALCHEMY_MODULE", _FakeAlchemyModule())

    bad_messages = [BadDump()]
    context = Context(
        system_prompt="test",
        messages=cast(list[Message], bad_messages),
    )

    with pytest.raises(TypeError, match="must return a dict"):
        await stream_alchemy_openai_completions(
            Model(provider="openai", id="gpt-4o-mini", api="openai-completions"),
            context,
            SimpleStreamOptions(),
        )


async def test_stream_alchemy_accepts_valid_model_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("tinyagent.alchemy_provider._ALCHEMY_MODULE", _FakeAlchemyModule())

    context = Context(
        system_prompt="test",
        messages=[UserMessage(content=[TextContent(text="hello")])],
    )

    response = await stream_alchemy_openai_completions(
        Model(provider="openai", id="gpt-4o-mini", api="openai-completions"),
        context,
        SimpleStreamOptions(),
    )

    assert response is not None
