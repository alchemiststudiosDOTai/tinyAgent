#!/usr/bin/env python3
"""Run one real tool-calling turn and print only type names.

Usage:
  uv run python docs/harness/tool_call_types_harness.py

Requires the optional external `tinyagent._alchemy` binding:
  https://github.com/tunahorse/tinyagent-alchemy
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Callable

from dotenv import load_dotenv

from tinyagent import Agent, AgentOptions
from tinyagent.agent_types import (
    AgentEvent,
    AgentTool,
    AgentToolResult,
    AssistantMessage,
    AssistantMessageEvent,
    Context,
    JsonObject,
    Model,
    SimpleStreamOptions,
    StreamResponse,
    TextContent,
    ToolResultMessage,
    UserMessage,
)
from tinyagent.alchemy_provider import OpenAICompatModel, stream_alchemy_openai_completions

DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_CHUTES_BASE_URL = "https://llm.chutes.ai/v1/chat/completions"
DEFAULT_MINIMAX_BASE_URL = "https://api.minimax.io/v1/chat/completions"
DEFAULT_OPENROUTER_MODEL = "google/gemini-2.0-flash-001"
DEFAULT_CHUTES_MODEL = "Qwen/Qwen3-Coder-Next-TEE"
DEFAULT_MINIMAX_MODEL = "MiniMax-M2.5"
DEFAULT_HARNESS_TIMEOUT_SECONDS = 120.0
DEFAULT_HARNESS_MAX_TOKENS = 512


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _csv(values: list[str]) -> str:
    return ",".join(_ordered_unique(values))


def _debug_enabled() -> bool:
    return os.getenv("HARNESS_DEBUG", "").lower() in {"1", "true", "yes", "on"}


def _resolve_provider_and_model() -> OpenAICompatModel | None:
    if os.getenv("OPENROUTER_API_KEY"):
        return OpenAICompatModel(
            provider="openrouter",
            api="openai-completions",
            id=os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL),
            base_url=os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL),
            max_tokens=int(os.getenv("HARNESS_MAX_TOKENS", str(DEFAULT_HARNESS_MAX_TOKENS))),
        )
    if os.getenv("CHUTES_API_KEY"):
        return OpenAICompatModel(
            provider="chutes",
            api="openai-completions",
            id=os.getenv("CHUTES_MODEL", DEFAULT_CHUTES_MODEL),
            base_url=os.getenv("CHUTES_BASE_URL", DEFAULT_CHUTES_BASE_URL),
            max_tokens=int(os.getenv("HARNESS_MAX_TOKENS", str(DEFAULT_HARNESS_MAX_TOKENS))),
        )
    if os.getenv("MINIMAX_API_KEY"):
        return OpenAICompatModel(
            provider="minimax",
            api="minimax-completions",
            id=os.getenv("MINIMAX_MODEL", DEFAULT_MINIMAX_MODEL),
            base_url=os.getenv("MINIMAX_BASE_URL", DEFAULT_MINIMAX_BASE_URL),
            max_tokens=int(os.getenv("HARNESS_MAX_TOKENS", str(DEFAULT_HARNESS_MAX_TOKENS))),
        )
    return None


def _resolve_api_key(provider: str) -> str | None:
    env_map = {
        "openrouter": "OPENROUTER_API_KEY",
        "chutes": "CHUTES_API_KEY",
        "openai": "OPENAI_API_KEY",
        "minimax": "MINIMAX_API_KEY",
        "minimax-cn": "MINIMAX_CN_API_KEY",
    }
    env_key = env_map.get(provider.lower())
    if not env_key:
        return None
    return os.getenv(env_key)


class CapturingStreamResponse(StreamResponse):
    """Wraps a stream response and records assistant stream event types."""

    def __init__(self, inner: StreamResponse, sink: list[str]):
        self._inner = inner
        self._sink = sink

    async def result(self) -> AssistantMessage:
        return await self._inner.result()

    def __aiter__(self) -> AsyncIterator[AssistantMessageEvent]:
        return self

    async def __anext__(self) -> AssistantMessageEvent:
        event = await self._inner.__anext__()
        if event.type:
            self._sink.append(event.type)
            if _debug_enabled():
                print(f"assistant_stream_event={event.type}")
        return event


def _coerce_numeric_argument(args: JsonObject, name: str) -> float:
    raw = args[name]
    if isinstance(raw, bool) or not isinstance(raw, str | int | float):
        raise RuntimeError(f"Tool argument `{name}` must be numeric")
    try:
        return float(raw)
    except ValueError as e:  # pragma: no cover - defensive for malformed provider output
        raise RuntimeError(f"Tool argument `{name}` must be numeric") from e


async def execute_add_once(
    tool_call_id: str,
    args: JsonObject,
    signal: asyncio.Event | None,
    on_update: Callable[[AgentToolResult], None],
) -> AgentToolResult:
    del tool_call_id, signal, on_update
    a = _coerce_numeric_argument(args, "a")
    b = _coerce_numeric_argument(args, "b")
    return AgentToolResult(content=[TextContent(text=str(int(a + b)))])


async def main() -> None:
    load_dotenv()

    model = _resolve_provider_and_model()
    if model is None:
        print("SKIPPED: missing OPENROUTER_API_KEY, CHUTES_API_KEY, or MINIMAX_API_KEY")
        return

    assistant_stream_event_types: list[str] = []
    agent_event_types: list[str] = []
    agent_event_class_types: list[str] = []

    async def stream_fn(
        model: Model,
        context: Context,
        options: SimpleStreamOptions,
    ) -> StreamResponse:
        response = await stream_alchemy_openai_completions(model, context, options)
        return CapturingStreamResponse(response, assistant_stream_event_types)

    tool = AgentTool(
        name="add_numbers",
        description="Add two numbers and return the integer sum.",
        parameters={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["a", "b"],
        },
        execute=execute_add_once,
    )

    agent = Agent(
        AgentOptions(
            stream_fn=stream_fn,
            get_api_key=_resolve_api_key,
        )
    )
    agent.set_model(model)
    agent.set_tools([tool])
    agent.set_system_prompt(
        "You are a strict test assistant. "
        "For this task, call add_numbers exactly once, then return only the result."
    )

    def on_event(event: AgentEvent) -> None:
        agent_event_class_types.append(type(event).__name__)
        agent_event_types.append(event.type)
        if _debug_enabled():
            print(f"agent_event={event.type}")

    unsubscribe = agent.subscribe(on_event)
    try:
        timeout_seconds = float(
            os.getenv("HARNESS_TIMEOUT_SECONDS", str(DEFAULT_HARNESS_TIMEOUT_SECONDS))
        )
        result = await asyncio.wait_for(
            agent.prompt(
                "Use add_numbers exactly once with a=17 and b=25. Respond only with the result."
            ),
            timeout=timeout_seconds,
        )
    finally:
        unsubscribe()

    message_types = [type(message).__name__ for message in agent.state.messages]

    content_types: list[str] = []
    for message in agent.state.messages:
        if not isinstance(message, UserMessage | AssistantMessage | ToolResultMessage):
            continue
        for item in message.content:
            if item is None:
                continue
            content_types.append(type(item).__name__)

    tool_results = [m for m in agent.state.messages if isinstance(m, ToolResultMessage)]
    if len(tool_results) != 1:
        raise RuntimeError(f"Expected exactly one tool call, got {len(tool_results)}")

    print(f"agent_event_types={_csv(agent_event_types)}")
    print(f"agent_event_class_types={_csv(agent_event_class_types)}")
    print(f"assistant_stream_event_types={_csv(assistant_stream_event_types)}")
    print(f"message_types={_csv(message_types)}")
    print(f"content_types={_csv(content_types)}")
    print(f"result_type={type(result).__name__}")


if __name__ == "__main__":
    asyncio.run(main())
