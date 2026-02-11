"""Tests that tinyAgent type contracts hold at runtime."""

import pytest

from tinyagent.agent_tool_execution import validate_tool_arguments
from tinyagent.agent_types import (
    STOP_REASONS,
    AgentTool,
    AssistantContent,
    AssistantMessage,
    ToolCallContent,
    ToolResultMessage,
    UserMessage,
)
from tinyagent.proxy_event_handlers import (
    _is_text_content,
    _is_thinking_content,
    _is_tool_call,
)

# -- Type guard contracts --


class TestTypeGuards:
    """Type guards correctly narrow AssistantContent."""

    def test_text_content_identified(self) -> None:
        content: AssistantContent = {"type": "text", "text": "hello"}
        assert _is_text_content(content) is True

    def test_thinking_content_identified(self) -> None:
        content: AssistantContent = {"type": "thinking", "thinking": "hmm"}
        assert _is_thinking_content(content) is True

    def test_tool_call_identified(self) -> None:
        content: AssistantContent = {
            "type": "tool_call",
            "id": "tc_1",
            "name": "search",
            "arguments": {},
        }
        assert _is_tool_call(content) is True

    def test_text_guard_rejects_thinking(self) -> None:
        content: AssistantContent = {"type": "thinking", "thinking": "hmm"}
        assert _is_text_content(content) is False

    def test_guards_handle_none(self) -> None:
        assert _is_text_content(None) is False
        assert _is_thinking_content(None) is False
        assert _is_tool_call(None) is False


# -- Message role contracts --


class TestMessageRoles:
    """Messages use correct role literals."""

    def test_user_message_role(self) -> None:
        msg: UserMessage = {"role": "user", "content": []}
        assert msg["role"] == "user"

    def test_assistant_message_role(self) -> None:
        msg: AssistantMessage = {"role": "assistant", "content": []}
        assert msg["role"] == "assistant"

    def test_tool_result_message_role(self) -> None:
        msg: ToolResultMessage = {
            "role": "tool_result",
            "tool_call_id": "x",
            "content": [],
        }
        assert msg["role"] == "tool_result"


# -- StopReason contracts --


class TestStopReasons:
    """StopReason literal values match STOP_REASONS set."""

    def test_stop_reasons_not_empty(self) -> None:
        assert len(STOP_REASONS) > 0

    def test_known_stop_reasons_present(self) -> None:
        expected = ("complete", "error", "aborted", "tool_calls", "stop", "length", "tool_use")
        for reason in expected:
            assert reason in STOP_REASONS, f"{reason} missing from STOP_REASONS"

    def test_stop_reasons_immutable(self) -> None:
        with pytest.raises(AttributeError):
            STOP_REASONS.add("bogus")  # type: ignore[attr-defined]


# -- Tool argument validation --


class TestToolArgumentValidation:
    """validate_tool_arguments returns arguments from tool calls."""

    def test_returns_arguments(self) -> None:
        tool = AgentTool(
            name="search",
            description="Search",
            parameters={"type": "object", "properties": {"query": {"type": "string"}}},
        )
        tool_call: ToolCallContent = {
            "type": "tool_call",
            "id": "tc_1",
            "name": "search",
            "arguments": {"query": "hello"},
        }
        result = validate_tool_arguments(tool, tool_call)
        assert result == {"query": "hello"}

    def test_missing_arguments_returns_empty(self) -> None:
        tool = AgentTool(name="noop", description="No-op", parameters={})
        tool_call: ToolCallContent = {"type": "tool_call", "id": "tc_2", "name": "noop"}
        result = validate_tool_arguments(tool, tool_call)
        assert result == {}


# -- Duplicate type guard drift detection --


class TestNoDuplicateGuardDrift:
    """Duplicate _is_text_content in openrouter_provider must match proxy_event_handlers."""

    def test_openrouter_text_guard_matches(self) -> None:
        from tinyagent.openrouter_provider import _is_text_content as or_guard

        text: AssistantContent = {"type": "text", "text": "hi"}
        thinking: AssistantContent = {"type": "thinking", "thinking": "hmm"}

        assert or_guard(text) == _is_text_content(text)
        assert or_guard(thinking) == _is_text_content(thinking)
        assert or_guard(None) == _is_text_content(None)
