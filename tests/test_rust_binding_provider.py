"""Unit tests for the typed Rust binding provider."""

from __future__ import annotations

from typing import cast

import pytest
from pydantic import ValidationError

from tinyagent.agent_types import (
    Context,
    Message,
    Model,
    SimpleStreamOptions,
    TextContent,
    UserMessage,
)
from tinyagent.rust_binding_provider import (
    DEFAULT_BASE_URLS,
    RustBindingModel,
    _build_context_payload,
    _build_model_payload,
    _get_binding_module,
    _resolve_api_key,
    _resolve_model_api,
    stream_rust_binding,
)


def test_resolve_model_api_defaults_to_kimi_anthropic_path() -> None:
    model = Model(provider="kimi", id="kimi-coding", api="")
    assert _resolve_model_api(model, "kimi") == "anthropic-messages"


def test_resolve_model_api_defaults_to_minimax_path() -> None:
    model = Model(provider="minimax", id="MiniMax-M2.5", api="")
    assert _resolve_model_api(model, "minimax") == "minimax-completions"


def test_build_model_payload_uses_provider_default_base_url() -> None:
    payload = _build_model_payload(RustBindingModel(provider="kimi", id="kimi-coding"))
    assert payload.base_url == DEFAULT_BASE_URLS["kimi"]
    assert payload.api == "anthropic-messages"


def test_resolve_api_key_supports_kimi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KIMI_API_KEY", "env-kimi")
    model = RustBindingModel(provider="kimi", id="kimi-coding")
    assert _resolve_api_key(model, SimpleStreamOptions()) == "env-kimi"


def test_rust_binding_model_rejects_legacy_api_alias() -> None:
    with pytest.raises(ValidationError, match="openai-completions"):
        RustBindingModel.model_validate(
            {
                "provider": "openai",
                "id": "gpt-4o-mini",
                "api": "openai",
            }
        )


def test_get_binding_module_falls_back_to_top_level_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imported: list[str] = []
    fallback_module = _FakeBindingModule()

    def fake_import_module(name: str) -> object:
        imported.append(name)
        if name == "tinyagent._alchemy":
            raise ModuleNotFoundError(name)
        if name == "_alchemy":
            return fallback_module
        raise AssertionError(f"unexpected import: {name}")

    monkeypatch.setattr("tinyagent.rust_binding_provider._BINDING_MODULE", None)
    monkeypatch.setattr(
        "tinyagent.rust_binding_provider.importlib.import_module",
        fake_import_module,
    )

    resolved = _get_binding_module()

    assert resolved is fallback_module
    assert imported == ["tinyagent._alchemy", "_alchemy"]


def test_build_context_payload_serializes_tools() -> None:
    context = Context(
        system_prompt="test",
        messages=[UserMessage(content=[TextContent(text="hello")])],
    )
    payload = _build_context_payload(context)

    assert payload.system_prompt == "test"
    assert payload.messages[0]["role"] == "user"
    assert payload.tools is None


class _FakeHandle:
    def next_event(self) -> object | None:
        return None

    def result(self) -> object:
        return {
            "role": "assistant",
            "content": [{"type": "text", "text": "ok"}],
            "stop_reason": "stop",
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


class _FakeBindingModule:
    def __init__(self) -> None:
        self.model: dict[str, object] | None = None
        self.context: dict[str, object] | None = None
        self.options: dict[str, object] | None = None

    def openai_completions_stream(
        self,
        model: dict[str, object],
        context: dict[str, object],
        options: dict[str, object],
    ) -> _FakeHandle:
        self.model = model
        self.context = context
        self.options = options
        return _FakeHandle()


async def test_stream_rust_binding_serializes_typed_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_module = _FakeBindingModule()
    monkeypatch.setattr("tinyagent.rust_binding_provider._BINDING_MODULE", fake_module)

    model = RustBindingModel(
        provider="kimi",
        id="kimi-coding",
        headers={"X-Test": "1"},
        reasoning="high",
    )
    context = Context(
        system_prompt="test",
        messages=[UserMessage(content=[TextContent(text="hello")])],
    )
    options = SimpleStreamOptions(api_key="kimi-key", temperature=0.2, max_tokens=32)

    response = await stream_rust_binding(model, context, options)

    assert response is not None
    assert fake_module.model == {
        "id": "kimi-coding",
        "provider": "kimi",
        "api": "anthropic-messages",
        "base_url": "https://api.kimi.com/coding",
        "headers": {"X-Test": "1"},
        "reasoning": "high",
        "context_window": 128_000,
        "max_tokens": 4096,
    }
    assert fake_module.context is not None
    assert fake_module.context["messages"] == [
        message.model_dump(exclude_none=True) for message in context.messages
    ]
    assert fake_module.options == {
        "api_key": "kimi-key",
        "temperature": 0.2,
        "max_tokens": 32,
    }


async def test_stream_rust_binding_rejects_message_without_model_dump(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("tinyagent.rust_binding_provider._BINDING_MODULE", _FakeBindingModule())

    bad_messages = [object()]
    context = Context(system_prompt="test", messages=cast(list[Message], bad_messages))

    with pytest.raises(TypeError, match=r"context\.messages"):
        await stream_rust_binding(
            RustBindingModel(provider="openai", id="gpt-4o-mini"),
            context,
            SimpleStreamOptions(),
        )
