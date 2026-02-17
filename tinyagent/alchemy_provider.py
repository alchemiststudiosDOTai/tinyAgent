"""Alchemy (Rust) provider for tinyagent.

This provider uses the Rust crate `alchemy-llm` via a small PyO3 binding
(`bindings/alchemy_llm_py`).

Important limitations:
- Only OpenAI-compatible `/chat/completions` streaming is supported.
- Image blocks are not supported yet.
- Python receives events by calling a blocking `next_event()` method in a thread,
  so it is real-time but has more overhead than a native async generator.

Build/install the binding first (from repo root):

    python -m pip install maturin
    cd bindings/alchemy_llm_py
    maturin develop

"""

from __future__ import annotations

import asyncio
import importlib
import os
from dataclasses import dataclass
from typing import Any, Literal, Protocol, TypeAlias, cast

from .agent_types import (
    AgentTool,
    AssistantMessage,
    AssistantMessageEvent,
    Context,
    JsonObject,
    Model,
    SimpleStreamOptions,
)

ReasoningEffort: TypeAlias = Literal["minimal", "low", "medium", "high", "xhigh"]
ReasoningMode: TypeAlias = bool | ReasoningEffort


class _AlchemyModule(Protocol):
    def openai_completions_stream(
        self,
        model: dict[str, Any],
        context: dict[str, Any],
        options: dict[str, Any],
    ) -> Any: ...


_ALCHEMY_MODULE: _AlchemyModule | None = None

DEFAULT_OPENAI_COMPAT_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"

_USAGE_KEYS = frozenset({"input", "output", "cache_read", "cache_write", "total_tokens", "cost"})
_COST_KEYS = frozenset({"input", "output", "cache_read", "cache_write", "total"})


def _missing_keys(data: dict[str, object], required: frozenset[str]) -> list[str]:
    return sorted(key for key in required if key not in data)


def _validate_usage_contract(raw_usage: object, *, where: str) -> JsonObject:
    if not isinstance(raw_usage, dict):
        raise RuntimeError(f"{where}: usage must be a dict")

    usage = cast(dict[str, object], raw_usage)
    missing_usage = _missing_keys(usage, _USAGE_KEYS)
    if missing_usage:
        raise RuntimeError(f"{where}: usage missing key(s): {', '.join(missing_usage)}")

    cost_raw = usage.get("cost")
    if not isinstance(cost_raw, dict):
        raise RuntimeError(f"{where}: usage.cost must be a dict")

    cost = cast(dict[str, object], cost_raw)
    missing_cost = _missing_keys(cost, _COST_KEYS)
    if missing_cost:
        raise RuntimeError(f"{where}: usage.cost missing key(s): {', '.join(missing_cost)}")

    return cast(JsonObject, usage)


def _validate_assistant_message_contract(
    raw_message: object,
    *,
    where: str,
    require_usage: bool,
) -> AssistantMessage:
    if not isinstance(raw_message, dict):
        raise RuntimeError(f"{where}: assistant message must be a dict")

    message = cast(dict[str, object], raw_message)

    if require_usage:
        _validate_usage_contract(message.get("usage"), where=where)

    return cast(AssistantMessage, message)


def _get_alchemy_module() -> _AlchemyModule:
    global _ALCHEMY_MODULE
    if _ALCHEMY_MODULE is None:
        package = __package__ or "tinyagent"
        try:
            module = importlib.import_module(f"{package}._alchemy")
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "tinyagent._alchemy is not installed. "
                "Build it via `maturin develop` in the project root"
            ) from e
        _ALCHEMY_MODULE = cast(_AlchemyModule, module)
    return _ALCHEMY_MODULE


@dataclass
class OpenAICompatModel(Model):
    """Model config for OpenAI-compatible chat/completions endpoints."""

    provider: str = "openrouter"
    id: str = "moonshotai/kimi-k2.5"
    api: str = "openai-completions"

    base_url: str = DEFAULT_OPENAI_COMPAT_CHAT_COMPLETIONS_URL
    name: str | None = None
    headers: dict[str, str] | None = None

    context_window: int = 128_000
    max_tokens: int = 4096
    reasoning: ReasoningMode = False


@dataclass
class AlchemyStreamResponse:
    """StreamResponse backed by a Rust stream handle."""

    _handle: Any
    _final_message: AssistantMessage | None = None

    async def result(self) -> AssistantMessage:
        if self._final_message is not None:
            return self._final_message

        msg = await asyncio.to_thread(self._handle.result)
        final_message = _validate_assistant_message_contract(
            msg,
            where="result",
            require_usage=True,
        )
        self._final_message = final_message
        return final_message

    def __aiter__(self) -> AlchemyStreamResponse:
        return self

    async def __anext__(self) -> AssistantMessageEvent:
        ev = await asyncio.to_thread(self._handle.next_event)
        if ev is None:
            raise StopAsyncIteration
        if not isinstance(ev, dict):
            raise RuntimeError("alchemy_llm_py returned an invalid event")
        return cast(AssistantMessageEvent, ev)


def _convert_tools(tools: list[AgentTool] | None) -> list[dict[str, Any]] | None:
    if not tools:
        return None
    out: list[dict[str, Any]] = []
    for t in tools:
        out.append(
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters or {"type": "object", "properties": {}},
            }
        )
    return out


def _resolve_base_url(model: Model) -> str:
    base_url = getattr(model, "base_url", DEFAULT_OPENAI_COMPAT_CHAT_COMPLETIONS_URL)
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("Model `base_url` must be a non-empty string")
    return base_url.strip()


def _resolve_api_key(model: Model, options: SimpleStreamOptions) -> str | None:
    explicit = options.get("api_key")
    if explicit:
        return explicit

    provider = model.provider.strip().lower() if isinstance(model.provider, str) else ""
    if provider == "openai":
        return os.environ.get("OPENAI_API_KEY")
    if provider == "openrouter":
        return os.environ.get("OPENROUTER_API_KEY")

    return None


async def stream_alchemy_openai_completions(
    model: Model,
    context: Context,
    options: SimpleStreamOptions,
) -> AlchemyStreamResponse:
    """Stream using the Rust alchemy-llm implementation (OpenAI-compatible)."""

    alchemy_llm_py = _get_alchemy_module()

    base_url = _resolve_base_url(model)

    model_dict: dict[str, Any] = {
        "id": model.id,
        "provider": model.provider,
        "base_url": base_url,
        "name": getattr(model, "name", None),
        "headers": getattr(model, "headers", None),
        "reasoning": getattr(model, "reasoning", False),
        "context_window": getattr(model, "context_window", None),
        "max_tokens": getattr(model, "max_tokens", None),
    }

    context_dict: dict[str, Any] = {
        "system_prompt": context.system_prompt or "",
        "messages": context.messages,
        "tools": _convert_tools(context.tools),
    }

    options_dict: dict[str, Any] = {
        "api_key": _resolve_api_key(model, options),
        "temperature": options.get("temperature"),
        "max_tokens": options.get("max_tokens"),
    }

    handle = alchemy_llm_py.openai_completions_stream(
        model_dict,
        context_dict,
        options_dict,
    )

    return AlchemyStreamResponse(_handle=handle)


async def stream_alchemy_openrouter(
    model: Model,
    context: Context,
    options: SimpleStreamOptions,
) -> AlchemyStreamResponse:
    """Rust-backed stream compatible with OpenRouterModel and base_url overrides."""
    return await stream_alchemy_openai_completions(model, context, options)
