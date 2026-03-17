"""Targeted tests for agent event handling regressions."""

from __future__ import annotations

from collections.abc import Callable

from tinyagent.agent_types import (
    AgentMessage,
    AgentState,
    AssistantMessage,
    TextContent,
    ToolExecutionEndEvent,
    ToolExecutionStartEvent,
    TurnEndEvent,
    UserMessage,
)
from tinyagent.utils.agent_event_handler import AgentEventStateHandler


def _append_collector() -> tuple[list[AgentMessage], Callable[[AgentMessage], None]]:
    appended: list[AgentMessage] = []

    def _append(message: AgentMessage) -> None:
        appended.append(message)

    return appended, _append


def test_handle_agent_event_updates_pending_tool_calls_set() -> None:
    state = AgentState(pending_tool_calls={"existing"})
    partial_holder: list[AgentMessage | None] = [None]
    _, append_message = _append_collector()

    AgentEventStateHandler.handle_event(
        state,
        ToolExecutionStartEvent(tool_call_id="tc_1", tool_name="echo"),
        partial_holder,
        append_message,
    )
    AgentEventStateHandler.handle_event(
        state,
        ToolExecutionStartEvent(tool_call_id="tc_1", tool_name="echo"),
        partial_holder,
        append_message,
    )
    assert state.pending_tool_calls == {"existing", "tc_1"}

    AgentEventStateHandler.handle_event(
        state,
        ToolExecutionEndEvent(tool_call_id="tc_1", tool_name="echo"),
        partial_holder,
        append_message,
    )
    assert state.pending_tool_calls == {"existing"}


def test_handle_agent_event_turn_end_captures_assistant_error_message() -> None:
    state = AgentState()
    partial_holder: list[AgentMessage | None] = [None]
    _, append_message = _append_collector()

    assistant_error_message = AssistantMessage(
        content=[TextContent(text="")],
        error_message="provider failed",
    )
    AgentEventStateHandler.handle_event(
        state,
        TurnEndEvent(message=assistant_error_message),
        partial_holder,
        append_message,
    )
    assert state.error == "provider failed"


def test_handle_agent_event_turn_end_ignores_non_assistant_message() -> None:
    state = AgentState(error="keep-existing")
    partial_holder: list[AgentMessage | None] = [None]
    _, append_message = _append_collector()

    AgentEventStateHandler.handle_event(
        state,
        TurnEndEvent(message=UserMessage(content=[TextContent(text="hi")])),
        partial_holder,
        append_message,
    )
    assert state.error == "keep-existing"
