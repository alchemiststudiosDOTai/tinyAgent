"""Tests for agent event type guards and EventStream behavior."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from tinyagent.agent_types import (
    AgentEndEvent,
    AgentEvent,
    AgentMessage,
    AgentStartEvent,
    EventStream,
    MessageEndEvent,
    MessageStartEvent,
    MessageUpdateEvent,
    TextContent,
    ToolExecutionEndEvent,
    ToolExecutionStartEvent,
    ToolExecutionUpdateEvent,
    TurnEndEvent,
    TurnStartEvent,
    UserMessage,
    is_agent_end_event,
    is_message_end_event,
    is_message_event,
    is_message_start_or_update_event,
    is_tool_execution_end_event,
    is_tool_execution_event,
    is_tool_execution_start_event,
    is_turn_end_event,
)


@dataclass(frozen=True)
class _GuardExpectations:
    agent_end: bool
    turn_end: bool
    message_start_or_update: bool
    message_end: bool
    message_event: bool
    tool_start: bool
    tool_end: bool
    tool_event: bool


_EVENT_CASES: list[tuple[str, AgentEvent, _GuardExpectations]] = [
    (
        "agent_start",
        AgentStartEvent(),
        _GuardExpectations(False, False, False, False, False, False, False, False),
    ),
    (
        "agent_end",
        AgentEndEvent(messages=[]),
        _GuardExpectations(True, False, False, False, False, False, False, False),
    ),
    (
        "turn_start",
        TurnStartEvent(),
        _GuardExpectations(False, False, False, False, False, False, False, False),
    ),
    (
        "turn_end",
        TurnEndEvent(),
        _GuardExpectations(False, True, False, False, False, False, False, False),
    ),
    (
        "message_start",
        MessageStartEvent(),
        _GuardExpectations(False, False, True, False, True, False, False, False),
    ),
    (
        "message_update",
        MessageUpdateEvent(),
        _GuardExpectations(False, False, True, False, True, False, False, False),
    ),
    (
        "message_end",
        MessageEndEvent(),
        _GuardExpectations(False, False, False, True, True, False, False, False),
    ),
    (
        "tool_execution_start",
        ToolExecutionStartEvent(tool_call_id="tc_1", tool_name="echo"),
        _GuardExpectations(False, False, False, False, False, True, False, True),
    ),
    (
        "tool_execution_update",
        ToolExecutionUpdateEvent(tool_call_id="tc_1", tool_name="echo"),
        _GuardExpectations(False, False, False, False, False, False, False, True),
    ),
    (
        "tool_execution_end",
        ToolExecutionEndEvent(tool_call_id="tc_1", tool_name="echo"),
        _GuardExpectations(False, False, False, False, False, False, True, True),
    ),
]


@pytest.mark.parametrize(
    ("event", "expected"),
    [(event, expected) for _, event, expected in _EVENT_CASES],
    ids=[name for name, _, _ in _EVENT_CASES],
)
def test_agent_event_type_guards_cover_all_variants(
    event: AgentEvent,
    expected: _GuardExpectations,
) -> None:
    assert is_agent_end_event(event) is expected.agent_end
    assert is_turn_end_event(event) is expected.turn_end
    assert is_message_start_or_update_event(event) is expected.message_start_or_update
    assert is_message_end_event(event) is expected.message_end
    assert is_message_event(event) is expected.message_event
    assert is_tool_execution_start_event(event) is expected.tool_start
    assert is_tool_execution_end_event(event) is expected.tool_end
    assert is_tool_execution_event(event) is expected.tool_event


def _make_event_stream() -> EventStream:
    return EventStream(
        is_end_event=lambda event: isinstance(event, AgentEndEvent),
        get_result=lambda event: event.messages if isinstance(event, AgentEndEvent) else [],
    )


async def test_event_stream_yields_queued_event_before_end() -> None:
    stream = _make_event_stream()
    start_event = TurnStartEvent()
    stream.push(start_event)
    stream.end([])

    first = await stream.__anext__()
    assert first == start_event

    with pytest.raises(StopAsyncIteration):
        await stream.__anext__()


async def test_event_stream_raises_exception_after_draining_existing_events() -> None:
    stream = _make_event_stream()
    turn_start = TurnStartEvent()
    stream.push(turn_start)
    stream.set_exception(RuntimeError("boom"))

    assert await stream.__anext__() == turn_start
    with pytest.raises(RuntimeError, match="boom"):
        await stream.__anext__()


async def test_event_stream_result_propagates_exception() -> None:
    stream = _make_event_stream()
    stream.set_exception(RuntimeError("stream failed"))

    with pytest.raises(RuntimeError, match="stream failed"):
        await stream.result()


async def test_event_stream_result_from_agent_end_event() -> None:
    stream = _make_event_stream()
    expected_messages: list[AgentMessage] = [UserMessage(content=[TextContent(text="done")])]
    stream.push(AgentEndEvent(messages=expected_messages))

    assert await stream.result() == expected_messages
