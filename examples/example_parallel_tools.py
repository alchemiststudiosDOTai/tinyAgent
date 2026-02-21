"""Parallel tool execution demo.

Demonstrates that tinyAgent executes multiple tool calls concurrently
via asyncio.gather(). Uses a fake LLM stream so no API key is needed.

## What this shows

    User: "Get the weather in Paris, London, and Tokyo"
        │
        ▼
    Fake LLM returns 3 tool calls in one response
        │
        ▼
    ┌──────────────────────────────────────────────────┐
    │  execute_tool_calls (agent_tool_execution.py)    │
    │                                                  │
    │  1. Emit ToolExecutionStartEvent × 3             │
    │  2. asyncio.gather(                              │
    │       get_weather("Paris"),   ← 0.3s sleep       │
    │       get_weather("London"),  ← 0.3s sleep       │
    │       get_weather("Tokyo"),   ← 0.3s sleep       │
    │     )                                            │
    │  3. Emit ToolExecutionEndEvent × 3 (in order)    │
    └──────────────────────────────────────────────────┘
        │
        ▼
    All 3 tools complete in ~0.3s (not ~0.9s)
        │
        ▼
    Fake LLM summarizes the results

Usage:
    python examples/example_parallel_tools.py
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

from tinyagent import Agent, AgentOptions, extract_text
from tinyagent.agent_types import (
    AgentEvent,
    AgentTool,
    AgentToolResult,
    AgentToolUpdateCallback,
    AssistantMessage,
    AssistantMessageEvent,
    Context,
    JsonObject,
    Model,
    SimpleStreamOptions,
    StreamResponse,
    TextContent,
)

# ── Tools ──────────────────────────────────────────────────────────────
#
# Each tool sleeps for 0.3s to simulate an async I/O call (e.g. HTTP).
# With sequential execution this would take 0.9s for 3 calls.
# With parallel execution it takes ~0.3s.

FAKE_WEATHER: dict[str, str] = {
    "paris": "22°C, partly cloudy",
    "london": "16°C, light rain",
    "tokyo": "28°C, sunny and humid",
}


async def execute_get_weather(
    tool_call_id: str,
    args: dict[str, Any],
    signal: asyncio.Event | None,
    on_update: AgentToolUpdateCallback,
) -> AgentToolResult:
    city = args.get("city", "unknown")
    await asyncio.sleep(0.3)  # simulate network latency
    weather = FAKE_WEATHER.get(city.lower(), "no data")
    return AgentToolResult(content=[TextContent(type="text", text=f"{city}: {weather}")])


weather_tool = AgentTool(
    name="get_weather",
    description="Get current weather for a city",
    parameters={
        "type": "object",
        "properties": {"city": {"type": "string", "description": "City name"}},
        "required": ["city"],
    },
    execute=execute_get_weather,
)


# ── Fake LLM stream ──────────────────────────────────────────────────
#
# Turn 1: returns 3 tool calls (get_weather for each city)
# Turn 2: returns a text summary of the results


def _usage() -> JsonObject:
    return {
        "input": 10,
        "output": 5,
        "cache_read": 0,
        "cache_write": 0,
        "total_tokens": 15,
        "cost": {"input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_write": 0.0, "total": 0.0},
    }


def _tool_call_message() -> AssistantMessage:
    return {
        "role": "assistant",
        "content": [
            {
                "type": "tool_call",
                "id": "call_paris",
                "name": "get_weather",
                "arguments": {"city": "Paris"},
            },
            {
                "type": "tool_call",
                "id": "call_london",
                "name": "get_weather",
                "arguments": {"city": "London"},
            },
            {
                "type": "tool_call",
                "id": "call_tokyo",
                "name": "get_weather",
                "arguments": {"city": "Tokyo"},
            },
        ],
        "stop_reason": "tool_calls",
        "api": "fake",
        "provider": "fake",
        "model": "fake-model",
        "usage": _usage(),
        "timestamp": 0,
    }


def _summary_message() -> AssistantMessage:
    return {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": (
                    "Here's the weather:\n"
                    "- Paris: 22°C, partly cloudy\n"
                    "- London: 16°C, light rain\n"
                    "- Tokyo: 28°C, sunny and humid"
                ),
            }
        ],
        "stop_reason": "complete",
        "api": "fake",
        "provider": "fake",
        "model": "fake-model",
        "usage": _usage(),
        "timestamp": 0,
    }


class FakeStream:
    """Minimal StreamResponse that returns a pre-built message."""

    def __init__(self, message: AssistantMessage) -> None:
        self._message = message
        self._yielded = False

    async def result(self) -> AssistantMessage:
        return self._message

    def __aiter__(self) -> AsyncIterator[AssistantMessageEvent]:
        return self

    async def __anext__(self) -> AssistantMessageEvent:
        if self._yielded:
            raise StopAsyncIteration
        self._yielded = True
        return {"type": "done", "reason": "stop", "message": self._message}


class FakeProvider:
    """Fake LLM provider: turn 1 returns tool calls, turn 2 returns summary."""

    def __init__(self) -> None:
        self.call_count = 0

    async def stream(
        self, model: Model, context: Context, options: SimpleStreamOptions
    ) -> StreamResponse:
        self.call_count += 1
        if self.call_count == 1:
            return FakeStream(_tool_call_message())
        return FakeStream(_summary_message())


# ── Event logger ──────────────────────────────────────────────────────


def event_logger(event: AgentEvent) -> None:
    etype = getattr(event, "type", None)
    if etype == "tool_execution_start":
        name = getattr(event, "tool_name", "?")
        args = getattr(event, "args", {})
        city = args.get("city", "?") if isinstance(args, dict) else "?"
        print(f"  [START] {name}({city}) at t={time.perf_counter() - T0:.3f}s")
    elif etype == "tool_execution_end":
        name = getattr(event, "tool_name", "?")
        print(f"  [DONE]  {name} at t={time.perf_counter() - T0:.3f}s")
    elif etype == "turn_end":
        print("  ── turn end ──")


T0 = 0.0


# ── Main ──────────────────────────────────────────────────────────────


async def main() -> None:
    global T0  # noqa: PLW0603

    print("=" * 60)
    print("tinyAgent — Parallel Tool Execution Demo")
    print("=" * 60)
    print()
    print("3 weather lookups, each with 0.3s latency.")
    print("Sequential would take ~0.9s. Parallel takes ~0.3s.")
    print()

    provider = FakeProvider()
    agent = Agent(AgentOptions(stream_fn=provider.stream))
    agent.set_model(Model(provider="fake", id="fake-model"))
    agent.set_tools([weather_tool])
    agent.subscribe(event_logger)

    question = "Get the weather in Paris, London, and Tokyo"
    print(f"User: {question}\n")

    T0 = time.perf_counter()
    result = await agent.prompt(question)
    elapsed = time.perf_counter() - T0

    print()
    print(f"Assistant: {extract_text(result)}")
    print()
    print(f"Total time: {elapsed:.3f}s (parallel: ~0.3s, sequential would be: ~0.9s)")


if __name__ == "__main__":
    asyncio.run(main())
