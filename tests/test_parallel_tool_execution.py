"""Tests for parallel tool execution."""

import asyncio
from collections.abc import Callable

from tinyagent.agent_tool_execution import execute_tool_calls
from tinyagent.agent_types import (
    AgentEvent,
    AgentMessage,
    AgentTool,
    AgentToolResult,
    AssistantContent,
    AssistantMessage,
    EventStream,
    JsonObject,
)


def _make_stream() -> EventStream:
    return EventStream(
        is_end_event=lambda e: False,
        get_result=lambda e: [],
    )


def _make_tool(name: str, delay: float = 0.0, result_text: str = "") -> AgentTool:
    async def execute(
        tool_call_id: str,
        args: JsonObject,
        signal: asyncio.Event | None,
        on_update: Callable[[AgentToolResult], None],
    ) -> AgentToolResult:
        if delay > 0:
            await asyncio.sleep(delay)
        return AgentToolResult(
            content=[{"type": "text", "text": result_text or f"{name} result"}],
        )

    return AgentTool(name=name, description=f"Test {name}", execute=execute)


def _make_message(*tool_names: str) -> AssistantMessage:
    content: list[AssistantContent | None] = [
        {"type": "tool_call", "id": f"tc_{i}", "name": name, "arguments": {}}
        for i, name in enumerate(tool_names)
    ]
    return {"role": "assistant", "content": content}


def _capturing_stream() -> tuple[EventStream, list[AgentEvent]]:
    """Create a stream that captures all pushed events."""
    stream = _make_stream()
    events: list[AgentEvent] = []
    original_push = stream.push

    def capturing_push(event: AgentEvent) -> None:
        events.append(event)
        original_push(event)

    stream.push = capturing_push  # type: ignore[method-assign]
    return stream, events


class TestParallelToolExecution:
    """Tool calls execute in parallel via asyncio.gather."""

    async def test_single_tool_executes(self) -> None:
        tool = _make_tool("search")
        message = _make_message("search")
        stream = _make_stream()
        result = await execute_tool_calls([tool], message, None, stream)
        assert len(result["tool_results"]) == 1
        assert result["tool_results"][0]["tool_name"] == "search"

    async def test_multiple_tools_return_in_order(self) -> None:
        tools = [_make_tool("a"), _make_tool("b"), _make_tool("c")]
        message = _make_message("a", "b", "c")
        stream = _make_stream()
        result = await execute_tool_calls(tools, message, None, stream)
        names = [r["tool_name"] for r in result["tool_results"]]
        assert names == ["a", "b", "c"]

    async def test_tools_execute_concurrently(self) -> None:
        """Three tools with 0.1s delay each finish in ~0.1s, not ~0.3s."""
        tools = [
            _make_tool("a", delay=0.1),
            _make_tool("b", delay=0.1),
            _make_tool("c", delay=0.1),
        ]
        message = _make_message("a", "b", "c")
        stream = _make_stream()
        start = asyncio.get_event_loop().time()
        await execute_tool_calls(tools, message, None, stream)
        elapsed = asyncio.get_event_loop().time() - start
        assert elapsed < 0.25, f"Expected parallel execution, took {elapsed:.2f}s"

    async def test_no_tool_calls_returns_empty(self) -> None:
        message: AssistantMessage = {
            "role": "assistant",
            "content": [{"type": "text", "text": "no tools"}],
        }
        stream = _make_stream()
        result = await execute_tool_calls([], message, None, stream)
        assert result["tool_results"] == []
        assert result["steering_messages"] is None


class TestParallelEventOrdering:
    """Events are emitted in correct order for parallel execution."""

    async def test_all_starts_before_any_end(self) -> None:
        tools = [_make_tool("a"), _make_tool("b"), _make_tool("c")]
        message = _make_message("a", "b", "c")
        stream, events = _capturing_stream()
        await execute_tool_calls(tools, message, None, stream)

        event_types = [getattr(e, "type", None) for e in events]
        start_indices = [i for i, t in enumerate(event_types) if t == "tool_execution_start"]
        end_indices = [i for i, t in enumerate(event_types) if t == "tool_execution_end"]

        assert len(start_indices) == 3
        assert len(end_indices) == 3
        assert max(start_indices) < min(end_indices)

    async def test_end_events_preserve_tool_order(self) -> None:
        tools = [_make_tool("a"), _make_tool("b"), _make_tool("c")]
        message = _make_message("a", "b", "c")
        stream, events = _capturing_stream()
        await execute_tool_calls(tools, message, None, stream)

        end_names = [
            getattr(e, "tool_name", None)
            for e in events
            if getattr(e, "type", None) == "tool_execution_end"
        ]
        assert end_names == ["a", "b", "c"]

    async def test_message_events_follow_end_events(self) -> None:
        tools = [_make_tool("x")]
        message = _make_message("x")
        stream, events = _capturing_stream()
        await execute_tool_calls(tools, message, None, stream)

        types = [getattr(e, "type", None) for e in events]
        assert types == [
            "tool_execution_start",
            "tool_execution_end",
            "message_start",
            "message_end",
        ]


class TestParallelErrorHandling:
    """Errors in one tool don't affect others during parallel execution."""

    async def test_error_in_one_tool_doesnt_affect_others(self) -> None:
        async def failing_execute(
            tool_call_id: str,
            args: JsonObject,
            signal: asyncio.Event | None,
            on_update: Callable[[AgentToolResult], None],
        ) -> AgentToolResult:
            raise ValueError("tool failed")

        tools = [
            _make_tool("good"),
            AgentTool(name="bad", description="failing", execute=failing_execute),
        ]
        message = _make_message("good", "bad")
        stream = _make_stream()

        result = await execute_tool_calls(tools, message, None, stream)
        assert len(result["tool_results"]) == 2
        assert result["tool_results"][0]["is_error"] is False
        assert result["tool_results"][1]["is_error"] is True

    async def test_unknown_tool_returns_error_result(self) -> None:
        message = _make_message("nonexistent")
        stream = _make_stream()
        result = await execute_tool_calls([], message, None, stream)
        assert len(result["tool_results"]) == 1
        assert result["tool_results"][0]["is_error"] is True

    async def test_tool_without_execute_returns_error(self) -> None:
        tool = AgentTool(name="no_exec", description="no execute fn")
        message = _make_message("no_exec")
        stream = _make_stream()
        result = await execute_tool_calls([tool], message, None, stream)
        assert result["tool_results"][0]["is_error"] is True


class TestParallelSteering:
    """Steering is checked once after all parallel tools complete."""

    async def test_steering_checked_after_all_tools(self) -> None:
        steering_check_count = 0

        async def get_steering() -> list[AgentMessage]:
            nonlocal steering_check_count
            steering_check_count += 1
            return [{"role": "user", "content": [{"type": "text", "text": "stop"}]}]

        tools = [_make_tool("a"), _make_tool("b")]
        message = _make_message("a", "b")
        stream = _make_stream()

        result = await execute_tool_calls(tools, message, None, stream, get_steering)
        assert steering_check_count == 1
        assert result["steering_messages"] is not None
        # Both tools completed with real results (not skipped)
        assert len(result["tool_results"]) == 2
        assert result["tool_results"][0]["is_error"] is False
        assert result["tool_results"][1]["is_error"] is False

    async def test_no_steering_returns_none(self) -> None:
        async def get_steering() -> list[AgentMessage]:
            return []

        tools = [_make_tool("a")]
        message = _make_message("a")
        stream = _make_stream()

        result = await execute_tool_calls(tools, message, None, stream, get_steering)
        assert result["steering_messages"] is None

    async def test_no_steering_callback_returns_none(self) -> None:
        tools = [_make_tool("a")]
        message = _make_message("a")
        stream = _make_stream()

        result = await execute_tool_calls(tools, message, None, stream, None)
        assert result["steering_messages"] is None
