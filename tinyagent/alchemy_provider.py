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
from dataclasses import dataclass
from typing import Any, Protocol, cast

from .agent_types import (
    AgentTool,
    AssistantMessage,
    AssistantMessageEvent,
    Context,
    JsonObject,
    Model,
    SimpleStreamOptions,
)


class _AlchemyModule(Protocol):
    def openai_completions_stream(
        self,
        model: dict[str, Any],
        context: dict[str, Any],
        options: dict[str, Any],
    ) -> Any: ...


_ALCHEMY_MODULE: _AlchemyModule | None = None

_USAGE_KEYS = frozenset({"input", "output", "cache_read", "cache_write", "total_tokens", "cost"})
_COST_KEYS = frozenset({"input", "output", "cache_read", "cache_write", "total"})
_EVENT_TYPES_WITH_PARTIAL = frozenset(
    {
        "start",
        "text_start",
        "text_delta",
        "text_end",
        "thinking_start",
        "thinking_delta",
        "thinking_end",
        "tool_call_start",
        "tool_call_delta",
        "tool_call_end",
    }
)
_ALLOWED_EVENT_TYPES = _EVENT_TYPES_WITH_PARTIAL | {"done", "error"}


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

    role = message.get("role")
    if role != "assistant":
        raise RuntimeError(f"{where}: assistant message role must be 'assistant'")

    content = message.get("content")
    if not isinstance(content, list):
        raise RuntimeError(f"{where}: assistant message content must be a list")

    if require_usage:
        _validate_usage_contract(message.get("usage"), where=where)

    return cast(AssistantMessage, message)


def _validate_event_contract(raw_event: object) -> AssistantMessageEvent:
    if not isinstance(raw_event, dict):
        raise RuntimeError("alchemy_llm_py returned an invalid event")

    event = cast(dict[str, object], raw_event)
    event_type = event.get("type")

    if not isinstance(event_type, str):
        raise RuntimeError("alchemy_llm_py event is missing a string `type`")

    if event_type not in _ALLOWED_EVENT_TYPES:
        raise RuntimeError(f"alchemy_llm_py returned unknown event type: {event_type}")

    if event_type in _EVENT_TYPES_WITH_PARTIAL:
        _validate_assistant_message_contract(
            event.get("partial"),
            where=f"event.{event_type}.partial",
            require_usage=True,
        )

    if event_type == "done":
        reason = event.get("reason")
        if not isinstance(reason, str):
            raise RuntimeError("alchemy_llm_py done event missing string `reason`")
        _validate_assistant_message_contract(
            event.get("message"),
            where="event.done.message",
            require_usage=True,
        )

    if event_type == "error":
        reason = event.get("reason")
        if not isinstance(reason, str):
            raise RuntimeError("alchemy_llm_py error event missing string `reason`")
        _validate_assistant_message_contract(
            event.get("error"),
            where="event.error.error",
            require_usage=True,
        )

    return cast(AssistantMessageEvent, event)


@dataclass
class OpenAICompatModel(Model):
    """Model config for OpenAI-compatible chat/completions endpoints."""

    # tinyagent's Model fields
    provider: str = "openrouter"
    id: str = "moonshotai/kimi-k2.5"
    api: str = "openai-completions"

    # additional fields used by the Rust binding
    base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    name: str | None = None
    headers: dict[str, str] | None = None

    # optional hints (not currently used by tinyagent itself)
    context_window: int = 128_000
    max_tokens: int = 4096
    reasoning: bool = False


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
        return _validate_event_contract(ev)


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


async def stream_alchemy_openai_completions(
    model: Model,
    context: Context,
    options: SimpleStreamOptions,
) -> AlchemyStreamResponse:
    """Stream using the Rust alchemy-llm implementation (OpenAI-compatible)."""

    alchemy_llm_py = _get_alchemy_module()

    base_url = getattr(model, "base_url", None)
    if not isinstance(base_url, str) or not base_url:
        raise ValueError("Model must have a non-empty `base_url` attribute")

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
        "api_key": options.get("api_key"),
        "temperature": options.get("temperature"),
        "max_tokens": options.get("max_tokens"),
    }

    # Start Rust streaming in-process.
    # The returned handle exposes blocking `next_event()` / `result()`.
    handle = alchemy_llm_py.openai_completions_stream(
        model_dict,
        context_dict,
        options_dict,
    )

    return AlchemyStreamResponse(_handle=handle)
