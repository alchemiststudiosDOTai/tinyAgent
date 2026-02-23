"""Parallel vs sequential tool execution comparison demo.

Demonstrates the performance difference between parallel (`execute_tool_calls`)
and a local sequential reference implementation. Each tool call has 0.3s latency.

With 3 tools:
  - Sequential: ~0.9s (0.3s + 0.3s + 0.3s)
  - Parallel:   ~0.3s (all run simultaneously)

Usage:
    python examples/example_parallel_tools.py
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, TypedDict, cast

from tinyagent import (
    AgentEvent,
    AgentTool,
    AgentToolResult,
    EventStream,
    ToolExecutionEndEvent,
    ToolExecutionStartEvent,
    ToolResultMessage,
    execute_tool_calls,
)

FAKE_WEATHER: dict[str, str] = {
    "paris": "22°C, partly cloudy",
    "london": "16°C, light rain",
    "tokyo": "28°C, sunny and humid",
    "new_york": "18°C, clear sky",
    "sydney": "25°C, warm breeze",
    "berlin": "14°C, overcast",
}


def _extract_tool_calls(assistant_message: dict[str, Any]) -> list[dict[str, Any]]:
    tool_calls: list[dict[str, Any]] = []
    for block in assistant_message.get("content", []):
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_call":
            tool_calls.append(block)
    return tool_calls


def _create_error_result(text: str) -> AgentToolResult:
    return AgentToolResult(content=[{"type": "text", "text": text}], details={})


def _create_tool_result_message(
    tool_call: dict[str, Any],
    result: AgentToolResult,
    *,
    is_error: bool,
) -> ToolResultMessage:
    return {
        "role": "tool_result",
        "tool_call_id": str(tool_call.get("id", "")),
        "tool_name": str(tool_call.get("name", "")),
        "content": result.content,
        "details": result.details,
        "is_error": is_error,
        "timestamp": int(asyncio.get_running_loop().time() * 1000),
    }


class SequentialToolExecutionResult(TypedDict):
    tool_results: list[ToolResultMessage]
    steering_messages: None


async def execute_get_weather(
    tool_call_id: str,
    args: dict[str, Any],
    signal: asyncio.Event | None,
    on_update: Any,
) -> AgentToolResult:
    city = args.get("city", "unknown")
    await asyncio.sleep(0.3)  # simulate network latency
    weather = FAKE_WEATHER.get(str(city).lower().replace(" ", "_"), "no data")
    return AgentToolResult(content=[{"type": "text", "text": f"{city}: {weather}"}])


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


async def execute_sequential(
    tools: list[AgentTool],
    assistant_message: dict[str, Any],
    stream: EventStream,
    signal: asyncio.Event | None = None,
) -> SequentialToolExecutionResult:
    """Execute tools one by one (sequential) for comparison."""

    tool_calls = _extract_tool_calls(assistant_message)
    tools_by_name = {tool.name: tool for tool in tools}
    results: list[ToolResultMessage] = []

    for tool_call in tool_calls:
        tool_call_id = str(tool_call.get("id", ""))
        tool_call_name = str(tool_call.get("name", ""))
        raw_args = tool_call.get("arguments", {})
        tool_call_args = raw_args if isinstance(raw_args, dict) else {}

        stream.push(
            ToolExecutionStartEvent(
                tool_call_id=tool_call_id,
                tool_name=tool_call_name,
                args=tool_call_args,
            )
        )

        tool = tools_by_name.get(tool_call_name)
        is_error = False

        if not tool:
            result = _create_error_result(f"Tool {tool_call_name} not found")
            is_error = True
        elif not tool.execute:
            result = _create_error_result(f"Tool {tool_call_name} has no execute function")
            is_error = True
        else:
            try:
                result = await tool.execute(
                    tool_call_id,
                    tool_call_args,
                    signal,
                    lambda partial: None,
                )
            except Exception as exc:  # noqa: BLE001
                result = _create_error_result(str(exc))
                is_error = True

        stream.push(
            ToolExecutionEndEvent(
                tool_call_id=tool_call_id,
                tool_name=tool_call_name,
                result=result,
                is_error=is_error,
            )
        )
        results.append(
            _create_tool_result_message(
                tool_call,
                result,
                is_error=is_error,
            )
        )

    return {"tool_results": results, "steering_messages": None}


T0 = 0.0


def event_logger(event: AgentEvent) -> None:
    etype = getattr(event, "type", None)
    if etype == "tool_execution_start":
        event_start = cast(ToolExecutionStartEvent, event)
        city = "?"
        if isinstance(event_start.args, dict):
            city = str(event_start.args.get("city", "?"))
        print(f"  [START] {event_start.tool_name}({city}) at t={time.perf_counter() - T0:.3f}s")
    elif etype == "tool_execution_end":
        event_end = cast(ToolExecutionEndEvent, event)
        print(f"  [DONE]  {event_end.tool_name} at t={time.perf_counter() - T0:.3f}s")


class LoggingEventStream(EventStream):
    """EventStream that also logs events for the demo."""

    def push(self, event: AgentEvent) -> None:
        event_logger(event)
        super().push(event)


async def run_parallel(cities: list[str]) -> float:
    """Run tools in parallel (default tinyAgent behavior)."""
    global T0

    print(f"\n{'─' * 60}")
    print(f"PARALLEL EXECUTION: {', '.join(cities)}")
    print(f"{'─' * 60}")

    stream = LoggingEventStream(
        is_end_event=lambda e: False,
        get_result=lambda e: [],
    )

    T0 = time.perf_counter()
    message = {
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
    }

    result = await execute_tool_calls(
        tools=[weather_tool],
        assistant_message=cast(Any, message),
        stream=stream,
        signal=None,
    )

    elapsed = time.perf_counter() - T0
    print(f"\n  Results: {len(result['tool_results'])} tools completed")
    print(f"  Total time: {elapsed:.3f}s")
    print("  Expected: ~0.3s (all 3 run simultaneously)")
    return elapsed


async def run_sequential(cities: list[str]) -> float:
    """Run tools sequentially (one at a time)."""
    global T0

    print(f"\n{'─' * 60}")
    print(f"SEQUENTIAL EXECUTION: {', '.join(cities)}")
    print(f"{'─' * 60}")

    stream = LoggingEventStream(
        is_end_event=lambda e: False,
        get_result=lambda e: [],
    )

    T0 = time.perf_counter()
    message = {
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
    }

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


async def main() -> None:
    print("=" * 60)
    print("tinyAgent — Parallel vs Sequential Tool Execution")
    print("=" * 60)
    print()
    print("Each weather lookup has 0.3s simulated network latency.")
    print("With 3 tools:")
    print("  - Sequential: ~0.9s (0.3s + 0.3s + 0.3s)")
    print("  - Parallel:   ~0.3s (all run simultaneously)")

    cities_parallel = ["Paris", "London", "Berlin"]
    time_parallel = await run_parallel(cities_parallel)

    cities_sequential = ["Tokyo", "Sydney", "New York"]
    time_sequential = await run_sequential(cities_sequential)

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
