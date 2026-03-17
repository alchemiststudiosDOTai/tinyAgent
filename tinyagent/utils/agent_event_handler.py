"""State updates for agent events."""

from __future__ import annotations

from collections.abc import Callable

from ..agent_types import (
    AgentEvent,
    AgentMessage,
    AgentState,
    AssistantMessage,
    is_message_end_event,
    is_message_start_or_update_event,
    is_tool_execution_end_event,
    is_tool_execution_start_event,
    is_turn_end_event,
)


class AgentEventStateHandler:
    """Apply agent events to mutable AgentState."""

    @staticmethod
    def _on_message_start_or_update(
        state: AgentState,
        event: AgentEvent,
        partial_holder: list[AgentMessage | None],
        append_message: Callable[[AgentMessage], None],
    ) -> None:
        del append_message
        if not is_message_start_or_update_event(event):
            return
        partial_holder[0] = event.message
        state.stream_message = partial_holder[0]

    @staticmethod
    def _on_message_end(
        state: AgentState,
        event: AgentEvent,
        partial_holder: list[AgentMessage | None],
        append_message: Callable[[AgentMessage], None],
    ) -> None:
        partial_holder[0] = None
        state.stream_message = None
        if not is_message_end_event(event):
            return
        if event.message is not None:
            append_message(event.message)

    @staticmethod
    def _update_pending_tool_calls(state: AgentState, tool_call_id: str, *, is_start: bool) -> None:
        pending = set(state.pending_tool_calls)
        if is_start:
            pending.add(tool_call_id)
        else:
            pending.discard(tool_call_id)
        state.pending_tool_calls = pending

    @classmethod
    def _on_tool_execution_start(
        cls,
        state: AgentState,
        event: AgentEvent,
        partial_holder: list[AgentMessage | None],
        append_message: Callable[[AgentMessage], None],
    ) -> None:
        del partial_holder, append_message
        if not is_tool_execution_start_event(event):
            return
        cls._update_pending_tool_calls(state, event.tool_call_id, is_start=True)

    @classmethod
    def _on_tool_execution_end(
        cls,
        state: AgentState,
        event: AgentEvent,
        partial_holder: list[AgentMessage | None],
        append_message: Callable[[AgentMessage], None],
    ) -> None:
        del partial_holder, append_message
        if not is_tool_execution_end_event(event):
            return
        cls._update_pending_tool_calls(state, event.tool_call_id, is_start=False)

    @staticmethod
    def _on_turn_end(
        state: AgentState,
        event: AgentEvent,
        partial_holder: list[AgentMessage | None],
        append_message: Callable[[AgentMessage], None],
    ) -> None:
        del partial_holder, append_message
        if not is_turn_end_event(event):
            return
        if not isinstance(event.message, AssistantMessage):
            return
        error_message = event.message.error_message
        if isinstance(error_message, str) and error_message:
            state.error = error_message

    @staticmethod
    def _on_agent_end(
        state: AgentState,
        event: AgentEvent,
        partial_holder: list[AgentMessage | None],
        append_message: Callable[[AgentMessage], None],
    ) -> None:
        del event, partial_holder, append_message
        state.is_streaming = False
        state.stream_message = None

    @classmethod
    def handle_event(
        cls,
        state: AgentState,
        event: AgentEvent,
        partial_holder: list[AgentMessage | None],
        append_message: Callable[[AgentMessage], None],
    ) -> None:
        """Handle a single agent event, updating state and the partial holder."""

        handlers: dict[
            str,
            Callable[
                [AgentState, AgentEvent, list[AgentMessage | None], Callable[[AgentMessage], None]],
                None,
            ],
        ] = {
            "message_start": cls._on_message_start_or_update,
            "message_update": cls._on_message_start_or_update,
            "message_end": cls._on_message_end,
            "tool_execution_start": cls._on_tool_execution_start,
            "tool_execution_end": cls._on_tool_execution_end,
            "turn_end": cls._on_turn_end,
            "agent_end": cls._on_agent_end,
        }
        handler = handlers.get(event.type)
        if handler is None:
            return
        handler(state, event, partial_holder, append_message)
