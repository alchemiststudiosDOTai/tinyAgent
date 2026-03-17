"""Agent class built on top of the agent loop."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import TypeAlias, TypeGuard

from .agent_loop import agent_loop, agent_loop_continue
from .agent_types import (
    ZERO_USAGE,
    AgentContext,
    AgentEndEvent,
    AgentEvent,
    AgentLoopConfig,
    AgentMessage,
    AgentState,
    AgentTool,
    AssistantMessage,
    ImageContent,
    MaybeAwaitable,
    Message,
    MessageUpdateEvent,
    Model,
    StreamFn,
    TextContent,
    ThinkingBudgets,
    ThinkingContent,
    ThinkingLevel,
    ToolCallContent,
    ToolResultMessage,
    UserMessage,
    is_message_end_event,
    is_message_start_or_update_event,
    is_tool_execution_end_event,
    is_tool_execution_start_event,
    is_turn_end_event,
)
from .caching import add_cache_breakpoints


def _on_message_start_or_update(
    state: AgentState,
    event: AgentEvent,
    partial_holder: list[AgentMessage | None],
    append_message: Callable[[AgentMessage], None],
) -> None:
    if not is_message_start_or_update_event(event):
        return
    partial_holder[0] = event.message
    state.stream_message = partial_holder[0]


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


def _update_pending_tool_calls(state: AgentState, tool_call_id: str, *, is_start: bool) -> None:
    pending = set(state.pending_tool_calls)
    if is_start:
        pending.add(tool_call_id)
    else:
        pending.discard(tool_call_id)
    state.pending_tool_calls = pending


def _on_tool_execution_start(
    state: AgentState,
    event: AgentEvent,
    partial_holder: list[AgentMessage | None],
    append_message: Callable[[AgentMessage], None],
) -> None:
    if not is_tool_execution_start_event(event):
        return
    _update_pending_tool_calls(state, event.tool_call_id, is_start=True)


def _on_tool_execution_end(
    state: AgentState,
    event: AgentEvent,
    partial_holder: list[AgentMessage | None],
    append_message: Callable[[AgentMessage], None],
) -> None:
    if not is_tool_execution_end_event(event):
        return
    _update_pending_tool_calls(state, event.tool_call_id, is_start=False)


def _on_turn_end(
    state: AgentState,
    event: AgentEvent,
    partial_holder: list[AgentMessage | None],
    append_message: Callable[[AgentMessage], None],
) -> None:
    if not is_turn_end_event(event):
        return
    if not isinstance(event.message, AssistantMessage):
        return
    error_message = event.message.error_message
    if isinstance(error_message, str) and error_message:
        state.error = error_message


def _on_agent_end(
    state: AgentState,
    event: AgentEvent,
    partial_holder: list[AgentMessage | None],
    append_message: Callable[[AgentMessage], None],
) -> None:
    state.is_streaming = False
    state.stream_message = None


_AGENT_EVENT_HANDLERS: dict[
    str,
    Callable[
        [AgentState, AgentEvent, list[AgentMessage | None], Callable[[AgentMessage], None]], None
    ],
] = {
    "message_start": _on_message_start_or_update,
    "message_update": _on_message_start_or_update,
    "message_end": _on_message_end,
    "tool_execution_start": _on_tool_execution_start,
    "tool_execution_end": _on_tool_execution_end,
    "turn_end": _on_turn_end,
    "agent_end": _on_agent_end,
}


def _handle_agent_event(
    state: AgentState,
    event: AgentEvent,
    partial_holder: list[AgentMessage | None],
    append_message: Callable[[AgentMessage], None],
) -> None:
    """Handle a single agent event, updating state and partial message holder."""

    event_type = event.type

    handler = _AGENT_EVENT_HANDLERS.get(event_type)
    if handler is None:
        return

    handler(state, event, partial_holder, append_message)


def _is_nonempty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _assistant_content_item_has_meaningful_content(item: object) -> bool:
    if not item:
        return False

    if isinstance(item, ThinkingContent):
        return _is_nonempty_str(item.thinking)
    if isinstance(item, TextContent):
        return _is_nonempty_str(item.text)
    if isinstance(item, ToolCallContent):
        return _is_nonempty_str(item.name)

    return False


def _has_meaningful_content(partial: AgentMessage | None) -> bool:
    """Check if partial message has meaningful content worth saving."""

    if not isinstance(partial, AssistantMessage):
        return False
    if not partial.content:
        return False

    return any(_assistant_content_item_has_meaningful_content(item) for item in partial.content)


def extract_text(message: AgentMessage | None) -> str:
    """Extract concatenated text blocks from an agent/LLM message."""

    if not message:
        return ""
    if not isinstance(message, UserMessage | AssistantMessage | ToolResultMessage):
        return ""

    parts: list[str] = []
    for item in message.content:
        if isinstance(item, TextContent) and isinstance(item.text, str):
            parts.append(item.text)
    return "".join(parts)


def _create_error_message(model: Model, error: Exception, was_aborted: bool) -> AgentMessage:
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


def _is_llm_message(message: AgentMessage) -> TypeGuard[Message]:
    role = message.role
    return role in {"user", "assistant", "tool_result"}


async def default_convert_to_llm(messages: list[AgentMessage]) -> list[Message]:
    """Default convert_to_llm: keep only LLM-compatible messages."""

    return [message for message in messages if _is_llm_message(message)]


ConvertToLlmCallback: TypeAlias = Callable[[list[AgentMessage]], MaybeAwaitable[list[Message]]]
TransformContextCallback: TypeAlias = Callable[
    [list[AgentMessage], asyncio.Event | None],
    Awaitable[list[AgentMessage]],
]
ApiKeyResolverCallback: TypeAlias = Callable[[str], MaybeAwaitable[str | None]]


def _build_transform_context(
    user_transform: TransformContextCallback | None,
    enable_caching: bool,
) -> TransformContextCallback | None:
    """Build the final transform_context callback, optionally composing caching."""
    if not enable_caching:
        return user_transform
    if user_transform is None:
        return add_cache_breakpoints

    # Compose: run caching transform first, then user transform
    async def _composed(
        messages: list[AgentMessage], signal: asyncio.Event | None
    ) -> list[AgentMessage]:
        messages = await add_cache_breakpoints(messages, signal)
        return await user_transform(messages, signal)

    return _composed


@dataclass
class AgentOptions:
    """Options for configuring the Agent."""

    initial_state: AgentState | None = None
    convert_to_llm: ConvertToLlmCallback | None = None
    transform_context: TransformContextCallback | None = None
    steering_mode: str = "one-at-a-time"  # "all" or "one-at-a-time"
    follow_up_mode: str = "one-at-a-time"  # "all" or "one-at-a-time"
    stream_fn: StreamFn | None = None
    session_id: str | None = None
    get_api_key: ApiKeyResolverCallback | None = None
    thinking_budgets: ThinkingBudgets | None = None
    enable_prompt_caching: bool = False


class Agent:
    """Agent class that uses the agent loop directly."""

    def __init__(self, opts: AgentOptions | None = None):
        if opts is None:
            opts = AgentOptions()

        self._state = AgentState()

        if opts.initial_state:
            self._state = AgentState.model_validate(opts.initial_state)
        self._listeners: set[Callable[[AgentEvent], None]] = set()
        self._abort_event: asyncio.Event | None = None
        self._convert_to_llm = opts.convert_to_llm or default_convert_to_llm
        self._transform_context = _build_transform_context(
            opts.transform_context, opts.enable_prompt_caching
        )
        self._steering_queue: list[AgentMessage] = []
        self._follow_up_queue: list[AgentMessage] = []
        self._steering_mode: str = opts.steering_mode or "one-at-a-time"
        self._follow_up_mode: str = opts.follow_up_mode or "one-at-a-time"
        self.stream_fn: StreamFn | None = opts.stream_fn
        self._session_id: str | None = opts.session_id
        self.get_api_key: ApiKeyResolverCallback | None = opts.get_api_key
        self._running_prompt: asyncio.Future[None] | None = None
        self._thinking_budgets: ThinkingBudgets | None = opts.thinking_budgets

    @property
    def session_id(self) -> str | None:
        """Get the current session ID used for provider caching."""

        return self._session_id

    @session_id.setter
    def session_id(self, value: str | None) -> None:
        """Set the session ID for provider caching."""

        self._session_id = value

    @property
    def thinking_budgets(self) -> ThinkingBudgets | None:
        return self._thinking_budgets

    @thinking_budgets.setter
    def thinking_budgets(self, value: ThinkingBudgets | None) -> None:
        self._thinking_budgets = value

    @property
    def state(self) -> AgentState:
        return self._state

    def subscribe(self, fn: Callable[[AgentEvent], None]) -> Callable[[], None]:
        """Subscribe to agent events. Returns an unsubscribe function."""

        self._listeners.add(fn)
        return lambda: self._listeners.discard(fn)

    # State mutators
    def set_system_prompt(self, value: str) -> None:
        self._state.system_prompt = value

    def set_model(self, model: Model) -> None:
        self._state.model = model

    def set_thinking_level(self, level: ThinkingLevel) -> None:
        self._state.thinking_level = level

    def set_steering_mode(self, mode: str) -> None:
        self._steering_mode = mode

    def get_steering_mode(self) -> str:
        return self._steering_mode

    def set_follow_up_mode(self, mode: str) -> None:
        self._follow_up_mode = mode

    def get_follow_up_mode(self) -> str:
        return self._follow_up_mode

    def set_tools(self, tools: list[AgentTool]) -> None:
        self._state.tools = tools

    def replace_messages(self, messages: list[AgentMessage]) -> None:
        self._state.messages = messages.copy()

    def append_message(self, message: AgentMessage) -> None:
        self._state.messages = [*self._state.messages, message]

    def steer(self, message: AgentMessage) -> None:
        """Queue a steering message to interrupt the agent mid-run."""

        self._steering_queue.append(message)

    def follow_up(self, message: AgentMessage) -> None:
        """Queue a follow-up message to be processed after the agent finishes."""

        self._follow_up_queue.append(message)

    def clear_steering_queue(self) -> None:
        self._steering_queue = []

    def clear_follow_up_queue(self) -> None:
        self._follow_up_queue = []

    def clear_all_queues(self) -> None:
        self._steering_queue = []
        self._follow_up_queue = []

    def clear_messages(self) -> None:
        self._state.messages = []

    def abort(self) -> None:
        if self._abort_event:
            self._abort_event.set()

    async def wait_for_idle(self) -> None:
        if self._running_prompt:
            await self._running_prompt

    def reset(self) -> None:
        self._state.messages = []
        self._state.is_streaming = False
        self._state.stream_message = None
        self._state.pending_tool_calls = set()
        self._state.error = None
        self._steering_queue = []
        self._follow_up_queue = []

    def _build_input_messages(
        self,
        input_data: str | AgentMessage | list[AgentMessage],
        images: list[ImageContent] | None = None,
    ) -> list[AgentMessage]:
        """Normalize prompt input into a list of AgentMessage objects."""

        if isinstance(input_data, list):
            return input_data
        if isinstance(input_data, str):
            content: list[TextContent | ImageContent] = [TextContent(text=input_data)]
            if images:
                content.extend(images)
            return [
                UserMessage(
                    content=content,
                    timestamp=int(asyncio.get_event_loop().time() * 1000),
                )
            ]
        return [input_data]

    def _last_assistant_message(self) -> AgentMessage | None:
        for msg in reversed(self._state.messages):
            if msg.role == "assistant":
                return msg
        return None

    async def prompt(
        self,
        input_data: str | AgentMessage | list[AgentMessage],
        images: list[ImageContent] | None = None,
    ) -> AgentMessage:
        """Send a prompt and return the final assistant message."""

        if self._state.is_streaming:
            raise RuntimeError(
                "Agent is already processing a prompt. Use steer() or follow_up() to queue "
                "messages, or wait for completion."
            )

        model = self._state.model
        if not model:
            raise RuntimeError("No model configured")

        before = len(self._state.messages)
        msgs = self._build_input_messages(input_data, images)
        await self._run_loop(msgs)

        new_messages = self._state.messages[before:]
        for msg in reversed(new_messages):
            if msg.role == "assistant":
                return msg

        raise RuntimeError("No assistant message produced")

    async def prompt_text(
        self,
        input_data: str | AgentMessage | list[AgentMessage],
        images: list[ImageContent] | None = None,
    ) -> str:
        return extract_text(await self.prompt(input_data, images=images))

    def stream(
        self,
        input_data: str | AgentMessage | list[AgentMessage],
        images: list[ImageContent] | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """Stream agent events for a prompt."""

        async def _gen() -> AsyncIterator[AgentEvent]:
            if self._state.is_streaming:
                raise RuntimeError(
                    "Agent is already processing a prompt. Use steer() or follow_up() to queue "
                    "messages, or wait for completion."
                )

            model = self._state.model
            if not model:
                raise RuntimeError("No model configured")

            msgs = self._build_input_messages(input_data, images)

            self._setup_run_state()
            context, config = self._build_loop_context_and_config(model)
            partial_holder: list[AgentMessage | None] = [None]

            try:
                stream_iter = agent_loop(msgs, context, config, self._abort_event, self.stream_fn)

                async for event in stream_iter:
                    _handle_agent_event(self._state, event, partial_holder, self.append_message)
                    self._emit(event)
                    yield event

                self._handle_remaining_partial(partial_holder[0])

            except Exception as err:  # noqa: BLE001
                was_aborted = bool(self._abort_event and self._abort_event.is_set())
                error_msg = _create_error_message(model, err, was_aborted)
                self.append_message(error_msg)
                self._state.error = str(err)
                end_event = AgentEndEvent(messages=[error_msg])
                self._emit(end_event)
                yield end_event

            finally:
                self._cleanup_run_state()

        return _gen()

    def stream_text(
        self,
        input_data: str | AgentMessage | list[AgentMessage],
        images: list[ImageContent] | None = None,
    ) -> AsyncIterator[str]:
        """Stream just the assistant text deltas for a prompt."""

        async def _gen() -> AsyncIterator[str]:
            current = ""
            async for event in self.stream(input_data, images=images):
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

                new_text = extract_text(msg_obj)
                delta = new_text[len(current) :] if new_text.startswith(current) else new_text
                current = new_text
                if delta:
                    yield delta

        return _gen()

    async def continue_(self) -> AgentMessage:
        """Continue from current context (for retry after overflow)."""

        if self._state.is_streaming:
            raise RuntimeError(
                "Agent is already processing. Wait for completion before continuing.",
            )

        before = len(self._state.messages)
        messages = self._state.messages
        if len(messages) == 0:
            raise RuntimeError("No messages to continue from")
        if messages[-1].role == "assistant":
            raise RuntimeError("Cannot continue from message role: assistant")

        await self._run_loop(None)

        new_messages = self._state.messages[before:]
        for msg in reversed(new_messages):
            if msg.role == "assistant":
                return msg

        raise RuntimeError("No assistant message produced")

    async def _run_loop(self, messages: list[AgentMessage] | None = None) -> None:
        """Run the agent loop."""

        model = self._state.model
        if not model:
            raise RuntimeError("No model configured")

        self._setup_run_state()

        context, config = self._build_loop_context_and_config(model)
        partial_holder: list[AgentMessage | None] = [None]

        try:
            stream_iter = (
                agent_loop(messages, context, config, self._abort_event, self.stream_fn)
                if messages
                else agent_loop_continue(context, config, self._abort_event, self.stream_fn)
            )

            async for event in stream_iter:
                _handle_agent_event(self._state, event, partial_holder, self.append_message)
                self._emit(event)

            self._handle_remaining_partial(partial_holder[0])

        except Exception as err:  # noqa: BLE001
            was_aborted = bool(self._abort_event and self._abort_event.is_set())
            error_msg = _create_error_message(model, err, was_aborted)
            self.append_message(error_msg)
            self._state.error = str(err)
            self._emit(AgentEndEvent(messages=[error_msg]))

        finally:
            self._cleanup_run_state()

    def _setup_run_state(self) -> None:
        loop = asyncio.get_event_loop()
        self._running_prompt = loop.create_future()
        self._abort_event = asyncio.Event()
        self._state.is_streaming = True
        self._state.stream_message = None
        self._state.error = None

    def _build_loop_context_and_config(self, model: Model) -> tuple[AgentContext, AgentLoopConfig]:
        context = AgentContext(
            system_prompt=self._state.system_prompt,
            messages=self._state.messages.copy(),
            tools=self._state.tools,
        )

        config = AgentLoopConfig(
            model=model,
            convert_to_llm=self._convert_to_llm,
            transform_context=self._transform_context,
            get_api_key=self.get_api_key,
            get_steering_messages=self._get_steering_messages,
            get_follow_up_messages=self._get_follow_up_messages,
        )

        return context, config

    def _handle_remaining_partial(self, partial: AgentMessage | None) -> None:
        if partial and _has_meaningful_content(partial):
            self.append_message(partial)
        elif partial and self._abort_event and self._abort_event.is_set():
            raise RuntimeError("Request was aborted")

    def _cleanup_run_state(self) -> None:
        self._state.is_streaming = False
        self._state.stream_message = None
        self._state.pending_tool_calls = set()
        self._abort_event = None
        if self._running_prompt and not self._running_prompt.done():
            self._running_prompt.set_result(None)
        self._running_prompt = None

    async def _get_steering_messages(self) -> list[AgentMessage]:
        if self._steering_mode == "one-at-a-time":
            if self._steering_queue:
                first = self._steering_queue[0]
                self._steering_queue = self._steering_queue[1:]
                return [first]
            return []

        steering = self._steering_queue.copy()
        self._steering_queue = []
        return steering

    async def _get_follow_up_messages(self) -> list[AgentMessage]:
        if self._follow_up_mode == "one-at-a-time":
            if self._follow_up_queue:
                first = self._follow_up_queue[0]
                self._follow_up_queue = self._follow_up_queue[1:]
                return [first]
            return []

        follow_up = self._follow_up_queue.copy()
        self._follow_up_queue = []
        return follow_up

    def _emit(self, event: AgentEvent) -> None:
        for listener in self._listeners:
            listener(event)
