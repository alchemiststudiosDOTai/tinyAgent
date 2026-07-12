"""Targeted tests for agent event handling regressions."""

from __future__ import annotations

from tinyagent.agent import Agent, AgentOptions
from tinyagent.agent_types import (
    AgentState,
    AssistantMessage,
    TextContent,
    ToolExecutionEndEvent,
    ToolExecutionStartEvent,
    TurnEndEvent,
    UserMessage,
)


def _agent_with_state(state: AgentState) -> Agent:
    return Agent(AgentOptions(initial_state=state))


def test_apply_event_updates_pending_tool_calls_set() -> None:
    agent = _agent_with_state(AgentState(pending_tool_calls={"existing"}))

    agent._apply_event(ToolExecutionStartEvent(tool_call_id="tc_1", tool_name="echo"))
    agent._apply_event(ToolExecutionStartEvent(tool_call_id="tc_1", tool_name="echo"))
    assert agent.state.pending_tool_calls == {"existing", "tc_1"}

    agent._apply_event(ToolExecutionEndEvent(tool_call_id="tc_1", tool_name="echo"))
    assert agent.state.pending_tool_calls == {"existing"}


def test_apply_event_turn_end_captures_assistant_error_message() -> None:
    agent = _agent_with_state(AgentState())

    assistant_error_message = AssistantMessage(
        content=[TextContent(text="")],
        error_message="provider failed",
    )
    agent._apply_event(TurnEndEvent(message=assistant_error_message))
    assert agent.state.error == "provider failed"


def test_apply_event_turn_end_ignores_non_assistant_message() -> None:
    agent = _agent_with_state(AgentState(error="keep-existing"))

    agent._apply_event(TurnEndEvent(message=UserMessage(content=[TextContent(text="hi")])))
    assert agent.state.error == "keep-existing"
