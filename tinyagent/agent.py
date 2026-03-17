"""Agent class built on top of the agent loop."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from typing import TypeGuard

from .agent_loop import agent_loop, agent_loop_continue
from .agent_options import (
    AgentOptions,
    ApiKeyResolverCallback,
    TransformContextCallback,
)
from .agent_streaming import process_stream_events, stream_text_deltas
from .agent_types import (
    AgentContext,
    AgentEvent,
    AgentLoopConfig,
    AgentMessage,
    AgentState,
    AgentTool,
    AssistantMessage,
    ImageContent,
    Message,
    Model,
    StreamFn,
    TextContent,
    ThinkingBudgets,
    ToolResultMessage,
    UserMessage,
)
from .caching import add_cache_breakpoints

__all__ = ["Agent", "AgentOptions", "default_convert_to_llm", "extract_text"]


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


def _find_last_assistant_message(messages: list[AgentMessage]) -> AgentMessage | None:
    for message in reversed(messages):
        if message.role == "assistant":
            return message
    return None


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

    def set_system_prompt(self, value: str) -> None:
        self._state.system_prompt = value

    def set_model(self, model: Model) -> None:
        self._state.model = model

    def set_tools(self, tools: list[AgentTool]) -> None:
        self._state.tools = tools

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

    def _assert_not_streaming(self, message: str) -> None:
        if self._state.is_streaming:
            raise RuntimeError(message)

    def _require_model(self) -> Model:
        model = self._state.model
        if not model:
            raise RuntimeError("No model configured")
        return model

    def _assistant_message_from_new_messages(self, before: int) -> AgentMessage:
        new_messages = self._state.messages[before:]
        assistant_message = _find_last_assistant_message(new_messages)
        if assistant_message is None:
            raise RuntimeError("No assistant message produced")
        return assistant_message

    def _prepare_loop(self) -> tuple[Model, AgentContext, AgentLoopConfig]:
        model = self._require_model()
        self._setup_run_state()
        context, config = self._build_loop_context_and_config(model)
        return model, context, config

    async def _run_and_get_assistant_message(
        self, messages: list[AgentMessage] | None = None
    ) -> AgentMessage:
        before = len(self._state.messages)
        await self._run_loop(messages)
        return self._assistant_message_from_new_messages(before)

    def _drain_message_queue(self, queue_attr: str, mode: str) -> list[AgentMessage]:
        queue = list(getattr(self, queue_attr))
        if mode == "one-at-a-time":
            if not queue:
                return []
            setattr(self, queue_attr, queue[1:])
            return [queue[0]]

        setattr(self, queue_attr, [])
        return queue

    async def prompt(
        self,
        input_data: str | AgentMessage | list[AgentMessage],
        images: list[ImageContent] | None = None,
    ) -> AgentMessage:
        """Send a prompt and return the final assistant message."""

        self._assert_not_streaming(
            "Agent is already processing a prompt. Use steer() or follow_up() to queue "
            "messages, or wait for completion."
        )
        msgs = self._build_input_messages(input_data, images)
        return await self._run_and_get_assistant_message(msgs)

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
            self._assert_not_streaming(
                "Agent is already processing a prompt. Use steer() or follow_up() to queue "
                "messages, or wait for completion."
            )
            msgs = self._build_input_messages(input_data, images)
            model, context, config = self._prepare_loop()

            def _create_stream() -> AsyncIterator[AgentEvent]:
                return agent_loop(msgs, context, config, self._abort_event, self.stream_fn)

            async for event in process_stream_events(
                state=self._state,
                model=model,
                abort_event=self._abort_event,
                create_stream=_create_stream,
                emit=self._emit,
                cleanup_run_state=self._cleanup_run_state,
            ):
                yield event

        return _gen()

    def stream_text(
        self,
        input_data: str | AgentMessage | list[AgentMessage],
        images: list[ImageContent] | None = None,
    ) -> AsyncIterator[str]:
        """Stream just the assistant text deltas for a prompt."""

        async def _gen() -> AsyncIterator[str]:
            async for delta in stream_text_deltas(self.stream(input_data, images=images)):
                yield delta

        return _gen()

    async def continue_(self) -> AgentMessage:
        """Continue from current context (for retry after overflow)."""

        self._assert_not_streaming(
            "Agent is already processing. Wait for completion before continuing."
        )
        messages = self._state.messages
        if len(messages) == 0:
            raise RuntimeError("No messages to continue from")
        if messages[-1].role == "assistant":
            raise RuntimeError("Cannot continue from message role: assistant")

        return await self._run_and_get_assistant_message(None)

    async def _run_loop(self, messages: list[AgentMessage] | None = None) -> None:
        """Run the agent loop."""

        model, context, config = self._prepare_loop()

        def _create_stream() -> AsyncIterator[AgentEvent]:
            if messages:
                return agent_loop(messages, context, config, self._abort_event, self.stream_fn)
            return agent_loop_continue(context, config, self._abort_event, self.stream_fn)

        async for _ in process_stream_events(
            state=self._state,
            model=model,
            abort_event=self._abort_event,
            create_stream=_create_stream,
            emit=self._emit,
            cleanup_run_state=self._cleanup_run_state,
        ):
            pass

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

    def _cleanup_run_state(self) -> None:
        self._state.is_streaming = False
        self._state.stream_message = None
        self._state.pending_tool_calls = set()
        self._abort_event = None
        if self._running_prompt and not self._running_prompt.done():
            self._running_prompt.set_result(None)
        self._running_prompt = None

    async def _get_steering_messages(self) -> list[AgentMessage]:
        return self._drain_message_queue("_steering_queue", self._steering_mode)

    async def _get_follow_up_messages(self) -> list[AgentMessage]:
        return self._drain_message_queue("_follow_up_queue", self._follow_up_mode)

    def _emit(self, event: AgentEvent) -> None:
        for listener in self._listeners:
            listener(event)
