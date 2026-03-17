"""Streaming helpers for Agent runtime."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable

from .agent_types import (
    ZERO_USAGE,
    AgentEndEvent,
    AgentEvent,
    AgentMessage,
    AgentState,
    AssistantMessage,
    MessageUpdateEvent,
    Model,
    TextContent,
)
from .utils.agent_event_handler import AgentEventStateHandler
from .utils.message_content import has_meaningful_content


def create_error_message(model: Model, error: Exception, was_aborted: bool) -> AgentMessage:
    """Create an error message for the agent."""

    return AssistantMessage(
        content=[TextContent(text="")],
        api=model.api,
        provider=model.provider,
        model=model.id,
        usage=ZERO_USAGE,
        stop_reason="aborted" if was_aborted else "error",
        error_message=str(error),
        timestamp=int(asyncio.get_event_loop().time() * 1000),
    )


def _handle_remaining_partial(
    state: AgentState,
    partial: AgentMessage | None,
    abort_event: asyncio.Event | None,
) -> None:
    if partial and has_meaningful_content(partial):
        state.messages.append(partial)
    elif partial and abort_event and abort_event.is_set():
        raise RuntimeError("Request was aborted")


async def process_stream_events(
    *,
    state: AgentState,
    model: Model,
    abort_event: asyncio.Event | None,
    create_stream: Callable[[], AsyncIterator[AgentEvent]],
    emit: Callable[[AgentEvent], None],
    cleanup_run_state: Callable[[], None],
) -> AsyncIterator[AgentEvent]:
    """Process agent stream events and keep AgentState in sync."""

    partial_holder: list[AgentMessage | None] = [None]

    try:
        async for event in create_stream():
            AgentEventStateHandler.handle_event(state, event, partial_holder, state.messages.append)
            emit(event)
            yield event

        _handle_remaining_partial(state, partial_holder[0], abort_event)

    except Exception as err:  # noqa: BLE001
        was_aborted = bool(abort_event and abort_event.is_set())
        error_msg = create_error_message(model, err, was_aborted)
        state.messages.append(error_msg)
        state.error = str(err)
        end_event = AgentEndEvent(messages=[error_msg])
        emit(end_event)
        yield end_event

    finally:
        cleanup_run_state()


async def stream_text_deltas(events: AsyncIterator[AgentEvent]) -> AsyncIterator[str]:
    """Yield assistant text deltas from an Agent event stream."""

    current = ""
    async for event in events:
        if event.type != "message_update" or not isinstance(event, MessageUpdateEvent):
            continue

        msg_obj = event.message
        if not isinstance(msg_obj, AssistantMessage):
            continue

        ame = event.assistant_message_event
        if ame and ame.type == "text_delta" and ame.delta:
            delta = str(ame.delta)
            current += delta
            yield delta
            continue

        new_text = "".join(
            item.text
            for item in msg_obj.content
            if isinstance(item, TextContent) and isinstance(item.text, str)
        )
        delta = new_text[len(current) :] if new_text.startswith(current) else new_text
        current = new_text
        if delta:
            yield delta
