"""Parallel vs Sequential tool execution comparison demo.

Demonstrates the performance difference between parallel (asyncio.gather)
and sequential tool execution. Each tool has 0.3s latency.

With 3 tools:
  - Sequential: ~0.9s (0.3s + 0.3s + 0.3s)
  - Parallel:   ~0.3s (all run simultaneously)

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
    EventStream,
    JsonObject,
    Model,
    SimpleStreamOptions,
    StreamResponse,
    TextContent,
    ToolExecutionStartEvent,
    ToolExecutionEndEvent,
)
from tinyagent.agent_tool_execution import execute_tool_calls, ToolExecutionResult

# ── Tools ──────────────────────────────────────────────────────────────

FAKE_WEATHER: dict[str, str] = {
    "paris": "22°C, partly cloudy",
    "london": "16°C, light rain",
    "tokyo": "28°C, sunny and humid",
    "new_york": "18°C, clear sky",
    "sydney": "25°C, warm breeze",
    "berlin": "14°C, overcast",
}


async def execute_get_weather(
    tool_call_id: str,
    args: dict[str, Any],
    signal: asyncio.Event | None,
    on_update: AgentToolUpdateCallback,
) -> AgentToolResult:
    city = args.get("city", "unknown")
    await asyncio.sleep(0.3)  # simulate network latency
    weather = FAKE_WEATHER.get(city.lower().replace(" ", "_"), "no data")
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


# ── Sequential execution helper ─────────────────────────────────────────


async def execute_sequential(
    tools: list[AgentTool],
    assistant_message: AssistantMessage,
    stream: EventStream,
    signal: asyncio.Event | None = None,
) -> ToolExecutionResult:
    """Execute tools one by one (sequential) for comparison."""
    from tinyagent.agent_tool_execution import (
        _extract_tool_calls,
        _find_tool,
        _execute_single_tool,
        _create_tool_result_message,
        ToolResultMessage,
    )

    tool_calls = _extract_tool_calls(assistant_message)
    results: list[ToolResultMessage] = []

    for tool_call in tool_calls:
        tool_call_id = tool_call.get("id", "")
        tool_call_name = tool_call.get("name", "")
        tool_call_args = tool_call.get("arguments", {})
        tool = _find_tool(tools, tool_call_name)

        # Emit start
        stream.push(
            ToolExecutionStartEvent(
                tool_call_id=tool_call_id,
                tool_name=tool_call_name,
                args=tool_call_args,
            )
        )

        # Execute and wait
        result, is_error = await _execute_single_tool(tool, tool_call, signal, stream)

        # Emit end
        stream.push(
            ToolExecutionEndEvent(
                tool_call_id=tool_call_id,
                tool_name=tool_call_name,
                result=result,
                is_error=is_error,
            )
        )

        results.append(_create_tool_result_message(tool_call, result, is_error))

    return {"tool_results": results, "steering_messages": None}


# ── Fake LLM streams ───────────────────────────────────────────────────


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


def _tool_call_message(cities: list[str]) -> AssistantMessage:
    """Generate tool calls for given cities."""
    return {
        "role": "assistant",
        "content": [
            {
                "type": "tool_call",
                "id": f"call_{city.lower().replace(' ', '_')}",
                "name": "get_weather",
                "arguments": {"city": city},
            }
            for city in cities
        ],
        "stop_reason": "tool_calls",
        "api": "fake",
        "provider": "fake",
        "model": "fake-model",
        "usage": {
            "input": 10,
            "output": 5,
            "cache_read": 0,
            "cache_write": 0,
            "total_tokens": 15,
            "cost": {
                "input": 0.0,
                "output": 0.0,
                "cache_read": 0.0,
                "cache_write": 0.0,
                "total": 0.0,
            },
        },
        "timestamp": 0,
    }


def _summary_message(cities: list[str]) -> AssistantMessage:
    """Generate summary of weather results."""
    lines = [
        f"- {city}: {FAKE_WEATHER.get(city.lower().replace(' ', '_'), 'no data')}"
        for city in cities
    ]
    return {
        "role": "assistant",
        "content": [{"type": "text", "text": "Here's the weather:\n" + "\n".join(lines)}],
        "stop_reason": "complete",
        "api": "fake",
        "provider": "fake",
        "model": "fake-model",
        "usage": {
            "input": 10,
            "output": 5,
            "cache_read": 0,
            "cache_write": 0,
            "total_tokens": 15,
            "cost": {
                "input": 0.0,
                "output": 0.0,
                "cache_read": 0.0,
                "cache_write": 0.0,
                "total": 0.0,
            },
        },
        "timestamp": 0,
    }


# ── Event logger ──────────────────────────────────────────────────────

T0 = 0.0


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


class LoggingEventStream(EventStream):
    """EventStream that also logs events for the demo."""

    def push(self, event: AgentEvent) -> None:
        event_logger(event)
        super().push(event)


# ── Benchmark functions ───────────────────────────────────────────────


async def run_parallel(cities: list[str]) -> float:
    """Run tools in parallel (default tinyAgent behavior)."""
    global T0

    print(f"\n{'─' * 60}")
    print(f"PARALLEL EXECUTION: {', '.join(cities)}")
    print(f"{'─' * 60}")

    # Create event stream with dummy callbacks for the demo
    stream = LoggingEventStream(
        is_end_event=lambda e: False,
        get_result=lambda e: [],
    )

    T0 = time.perf_counter()
    message = _tool_call_message(cities)

    result = await execute_tool_calls(
        tools=[weather_tool],
        assistant_message=message,
        stream=stream,
        signal=None,
    )

    elapsed = time.perf_counter() - T0
    print(f"\n  Results: {len(result['tool_results'])} tools completed")
    print(f"  Total time: {elapsed:.3f}s")
    print(f"  Expected: ~{0.3:.1f}s (all 3 run simultaneously)")
    return elapsed


async def run_sequential(cities: list[str]) -> float:
    """Run tools sequentially (one at a time)."""
    global T0

    print(f"\n{'─' * 60}")
    print(f"SEQUENTIAL EXECUTION: {', '.join(cities)}")
    print(f"{'─' * 60}")

    # Create event stream with dummy callbacks for the demo
    stream = LoggingEventStream(
        is_end_event=lambda e: False,
        get_result=lambda e: [],
    )

    T0 = time.perf_counter()
    message = _tool_call_message(cities)

    result = await execute_sequential(
        tools=[weather_tool],
        assistant_message=message,
        stream=stream,
        signal=None,
    )

    elapsed = time.perf_counter() - T0
    print(f"\n  Results: {len(result['tool_results'])} tools completed")
    print(f"  Total time: {elapsed:.3f}s")
    print(f"  Expected: ~{0.3 * len(cities):.1f}s (0.3s × {len(cities)} sequential calls)")
    return elapsed


# ── Main ──────────────────────────────────────────────────────────────


async def main() -> None:
    print("=" * 60)
    print("tinyAgent — Parallel vs Sequential Tool Execution")
    print("=" * 60)
    print()
    print("Each weather lookup has 0.3s simulated network latency.")
    print("With 3 tools:")
    print("  - Sequential: ~0.9s (0.3s + 0.3s + 0.3s)")
    print("  - Parallel:   ~0.3s (all run simultaneously)")

    # Set 1: European cities (parallel)
    cities_parallel = ["Paris", "London", "Berlin"]
    time_parallel = await run_parallel(cities_parallel)

    # Set 2: Other cities (sequential)
    cities_sequential = ["Tokyo", "Sydney", "New York"]
    time_sequential = await run_sequential(cities_sequential)

    # Summary
    speedup = time_sequential / time_parallel if time_parallel > 0 else 0

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"\nParallel execution:   {time_parallel:.3f}s")
    print(f"Sequential execution: {time_sequential:.3f}s")
    print(f"\nSpeedup: {speedup:.1f}x faster with parallel execution")
    print(f"Time saved: {time_sequential - time_parallel:.3f}s")


if __name__ == "__main__":
    asyncio.run(main())
