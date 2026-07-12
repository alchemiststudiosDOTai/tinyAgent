"""Agent class built on top of the agent loop."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import TypeAlias, TypeGuard

from .agent_loop import agent_loop, agent_loop_continue
from .agent_types import (
    ZERO_USAGE,
    AfterToolCallFn,
    AgentContext,
    AgentEndEvent,
    AgentEvent,
    AgentLoopConfig,
    AgentMessage,
    AgentState,
    AgentTool,
    ApiKeyResolver,
    AssistantMessage,
    BeforeToolCallFn,
    ConvertToLlmFn,
    ImageContent,
    Message,
    MessageUpdateEvent,
    Model,
    ShouldStopAfterTurnFn,
    StreamFn,
    TextContent,
    ThinkingBudgets,
    ThinkingContent,
    ThinkingLevel,
    ToolCallContent,
    ToolResultMessage,
    TransformContextFn,
    UserMessage,
    is_agent_end_event,
    is_message_end_event,
    is_message_start_or_update_event,
    is_tool_execution_end_event,
    is_tool_execution_start_event,
    is_turn_end_event,
)
from .caching import add_cache_breakpoints

ConvertToLlmCallback: TypeAlias = ConvertToLlmFn
TransformContextCallback: TypeAlias = TransformContextFn
ApiKeyResolverCallback: TypeAlias = ApiKeyResolver


def _is_nonempty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_meaningful_content(partial: AgentMessage | None) -> bool:
    """Check if partial message has meaningful content worth saving."""

    if not isinstance(partial, AssistantMessage):
        return False

    for item in partial.content:
        if isinstance(item, ThinkingContent) and _is_nonempty_str(item.thinking):
            return True
        if isinstance(item, TextContent) and _is_nonempty_str(item.text):
            return True
        if isinstance(item, ToolCallContent) and _is_nonempty_str(item.name):
            return True
    return False


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
    before_tool_call: BeforeToolCallFn | None = None
    after_tool_call: AfterToolCallFn | None = None
    should_stop_after_turn: ShouldStopAfterTurnFn | None = None


class Agent:
    """Agent class that uses the agent loop directly."""

    def __init__(self, opts: AgentOptions | None = None):
        if opts is None:
            opts = AgentOptions()

        self._state = (
            AgentState.model_validate(opts.initial_state) if opts.initial_state else AgentState()
        )
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
        self._partial_message: AgentMessage | None = None
        self._thinking_budgets: ThinkingBudgets | None = opts.thinking_budgets
        self._before_tool_call = opts.before_tool_call
        self._after_tool_call = opts.after_tool_call
        self._should_stop_after_turn = opts.should_stop_after_turn

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

    async def prompt(
        self,
        input_data: str | AgentMessage | list[AgentMessage],
        images: list[ImageContent] | None = None,
    ) -> AgentMessage:
        """Send a prompt and return the final assistant message."""

        before = len(self._state.messages)
        async for _ in self._run(input_data, images):
            pass
        return self._last_new_assistant(before)

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

        return self._run(input_data, images)

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

        messages = self._state.messages
        if len(messages) == 0:
            raise RuntimeError("No messages to continue from")
        if messages[-1].role == "assistant":
            raise RuntimeError("Cannot continue from message role: assistant")

        before = len(messages)
        async for _ in self._run(None, None):
            pass
        return self._last_new_assistant(before)

    async def _run(
        self,
        input_data: str | AgentMessage | list[AgentMessage] | None,
        images: list[ImageContent] | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """Run the agent loop, applying each event to state and yielding it.

        `input_data=None` continues from the existing context instead of adding
        new prompt messages.
        """

        if self._state.is_streaming:
            raise RuntimeError(
                "Agent is already processing a prompt. Use steer() or follow_up() to queue "
                "messages, or wait for completion."
            )

        model = self._state.model
        if not model:
            raise RuntimeError("No model configured")

        messages = None if input_data is None else self._build_input_messages(input_data, images)

        self._setup_run_state()
        context, config = self._build_loop_context_and_config(model)

        try:
            stream_iter = (
                agent_loop(messages, context, config, self._abort_event, self.stream_fn)
                if messages is not None
                else agent_loop_continue(context, config, self._abort_event, self.stream_fn)
            )

            async for event in stream_iter:
                self._apply_event(event)
                self._emit(event)
                yield event

            self._handle_remaining_partial()

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

    def _apply_event(self, event: AgentEvent) -> None:
        """Update agent state in response to a loop event."""

        state = self._state
        if is_message_start_or_update_event(event):
            self._partial_message = event.message
            state.stream_message = event.message
        elif is_message_end_event(event):
            self._partial_message = None
            state.stream_message = None
            if event.message is not None:
                self.append_message(event.message)
        elif is_tool_execution_start_event(event):
            state.pending_tool_calls = state.pending_tool_calls | {event.tool_call_id}
        elif is_tool_execution_end_event(event):
            state.pending_tool_calls = state.pending_tool_calls - {event.tool_call_id}
        elif is_turn_end_event(event):
            message = event.message
            if isinstance(message, AssistantMessage) and message.error_message:
                state.error = message.error_message
        elif is_agent_end_event(event):
            state.is_streaming = False
            state.stream_message = None

    def _last_new_assistant(self, before: int) -> AgentMessage:
        """Return the last assistant message appended after index `before`."""

        for msg in reversed(self._state.messages[before:]):
            if msg.role == "assistant":
                return msg
        raise RuntimeError("No assistant message produced")

    def _setup_run_state(self) -> None:
        loop = asyncio.get_event_loop()
        self._running_prompt = loop.create_future()
        self._abort_event = asyncio.Event()
        self._partial_message = None
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
            before_tool_call=self._before_tool_call,
            after_tool_call=self._after_tool_call,
            should_stop_after_turn=self._should_stop_after_turn,
        )

        return context, config

    def _handle_remaining_partial(self) -> None:
        partial = self._partial_message
        if partial and _has_meaningful_content(partial):
            self.append_message(partial)
        elif partial and self._abort_event and self._abort_event.is_set():
            raise RuntimeError("Request was aborted")

    def _cleanup_run_state(self) -> None:
        self._state.is_streaming = False
        self._state.stream_message = None
        self._state.pending_tool_calls = set()
        self._abort_event = None
        self._partial_message = None
        if self._running_prompt and not self._running_prompt.done():
            self._running_prompt.set_result(None)
        self._running_prompt = None

    @staticmethod
    def _drain_queue(queue: list[AgentMessage], mode: str) -> list[AgentMessage]:
        count = 1 if mode == "one-at-a-time" else len(queue)
        taken = queue[:count]
        del queue[:count]
        return taken

    async def _get_steering_messages(self) -> list[AgentMessage]:
        return self._drain_queue(self._steering_queue, self._steering_mode)

    async def _get_follow_up_messages(self) -> list[AgentMessage]:
        return self._drain_queue(self._follow_up_queue, self._follow_up_mode)

    def _emit(self, event: AgentEvent) -> None:
        for listener in self._listeners:
            listener(event)
