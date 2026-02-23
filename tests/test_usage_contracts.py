"""Contract tests for usage serialization across the Rust/Python boundary.

These tests enforce two invariants:
1) Python -> Rust request payload forwarding must not silently drop fields.
2) Messages returned to callers must include the documented usage structure.
"""

from __future__ import annotations

import asyncio
import importlib
from collections.abc import AsyncIterator, Coroutine
from typing import Any, TypeVar, cast

import pytest

import tinyagent.alchemy_provider as alchemy_provider
from tinyagent import Agent, AgentOptions
from tinyagent.agent_types import (
    AgentContext,
    AgentLoopConfig,
    AgentMessage,
    AgentTool,
    AssistantMessage,
    AssistantMessageEvent,
    Context,
    JsonObject,
    Model,
    SimpleStreamOptions,
)

T = TypeVar("T")


class FakeHandle:
    """Small fake stream handle that mimics the PyO3 API shape."""

    def __init__(self, events: list[object], final_message: object) -> None:
        self._events = events
        self._index = 0
        self._final_message = final_message

    def next_event(self) -> object | None:
        if self._index >= len(self._events):
            return None
        event = self._events[self._index]
        self._index += 1
        return event

    def result(self) -> object:
        return self._final_message


class FakeAlchemyModule:
    """Captures payload passed by stream_alchemy_openai_completions."""

    def __init__(self, handle: FakeHandle) -> None:
        self._handle = handle
        self.captured_model: dict[str, Any] | None = None
        self.captured_context: dict[str, Any] | None = None
        self.captured_options: dict[str, Any] | None = None

    def openai_completions_stream(
        self,
        model: dict[str, Any],
        context: dict[str, Any],
        options: dict[str, Any],
    ) -> FakeHandle:
        self.captured_model = model
        self.captured_context = context
        self.captured_options = options
        return self._handle


class FakeStreamResponse:
    """Minimal StreamResponse implementation for Agent tests."""

    def __init__(
        self,
        events: list[AssistantMessageEvent],
        final_message: AssistantMessage,
    ) -> None:
        self._events = events
        self._index = 0
        self._final_message = final_message

    async def result(self) -> AssistantMessage:
        return self._final_message

    def __aiter__(self) -> AsyncIterator[AssistantMessageEvent]:
        return self

    async def __anext__(self) -> AssistantMessageEvent:
        if self._index >= len(self._events):
            raise StopAsyncIteration
        event = self._events[self._index]
        self._index += 1
        return event


def _run(coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro)


def _usage_payload() -> JsonObject:
    return {
        "input": 10,
        "output": 4,
        "cache_read": 1,
        "cache_write": 0,
        "total_tokens": 15,
        "cost": {
            "input": 0.0,
            "output": 0.0,
            "cache_read": 0.0,
            "cache_write": 0.0,
            "total": 0.0,
        },
    }


def _assistant_message(text: str) -> AssistantMessage:
    return {
        "role": "assistant",
        "content": [{"type": "text", "text": text}],
        "stop_reason": "complete",
        "api": "openai-completions",
        "provider": "openrouter",
        "model": "moonshotai/kimi-k2.5",
        "timestamp": 123,
        "usage": _usage_payload(),
    }


def test_alchemy_provider_forwards_full_payload_and_enforces_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _scenario() -> None:
        final_message = _assistant_message("hello")
        start_event: AssistantMessageEvent = {"type": "start", "partial": final_message}
        done_event: AssistantMessageEvent = {
            "type": "done",
            "reason": "stop",
            "message": final_message,
        }

        fake_module = FakeAlchemyModule(FakeHandle([start_event, done_event], final_message))
        monkeypatch.setattr(alchemy_provider, "_ALCHEMY_MODULE", fake_module)

        model = alchemy_provider.OpenAICompatModel(
            provider="openrouter",
            id="moonshotai/kimi-k2.5",
            base_url="https://openrouter.ai/api/v1/chat/completions",
            name="Kimi",
            headers={"X-Title": "contract-test"},
            reasoning=True,
            context_window=200_000,
            max_tokens=2_048,
        )
        context = Context(
            system_prompt="Be concise.",
            messages=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "hello"}],
                }
            ],
            tools=[
                AgentTool(
                    name="echo",
                    description="Echoes input",
                    parameters={"type": "object", "properties": {"text": {"type": "string"}}},
                )
            ],
        )
        options: SimpleStreamOptions = {
            "api_key": "k-test",
            "temperature": 0.2,
            "max_tokens": 77,
        }

        response = await alchemy_provider.stream_alchemy_openai_completions(model, context, options)

        seen_events: list[AssistantMessageEvent] = []
        async for event in response:
            seen_events.append(event)

        result = await response.result()

        assert fake_module.captured_model == {
            "id": "moonshotai/kimi-k2.5",
            "provider": "openrouter",
            "api": "openai-completions",
            "base_url": "https://openrouter.ai/api/v1/chat/completions",
            "name": "Kimi",
            "headers": {"X-Title": "contract-test"},
            "reasoning": True,
            "context_window": 200_000,
            "max_tokens": 2_048,
        }
        assert fake_module.captured_context is not None
        assert fake_module.captured_context["system_prompt"] == "Be concise."
        assert fake_module.captured_context["messages"] == context.messages
        assert fake_module.captured_context["tools"] == [
            {
                "name": "echo",
                "description": "Echoes input",
                "parameters": {"type": "object", "properties": {"text": {"type": "string"}}},
            }
        ]
        assert fake_module.captured_options == {
            "api_key": "k-test",
            "temperature": 0.2,
            "max_tokens": 77,
        }

        assert len(seen_events) == 2
        assert seen_events[-1].get("type") == "done"
        assert result["usage"] == _usage_payload()

    _run(_scenario())


def test_alchemy_provider_forwards_reasoning_effort_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _scenario() -> None:
        final_message = _assistant_message("hello")
        done_event: AssistantMessageEvent = {
            "type": "done",
            "reason": "stop",
            "message": final_message,
        }
        fake_module = FakeAlchemyModule(FakeHandle([done_event], final_message))
        monkeypatch.setattr(alchemy_provider, "_ALCHEMY_MODULE", fake_module)

        model = alchemy_provider.OpenAICompatModel(
            provider="openrouter",
            id="moonshotai/kimi-k2.5",
            base_url="https://openrouter.ai/api/v1/chat/completions",
            name="Kimi",
            headers={"X-Title": "contract-test"},
            reasoning="high",
            context_window=200_000,
            max_tokens=2_048,
        )
        context = Context(
            system_prompt="Be concise.",
            messages=[{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
        )
        options: SimpleStreamOptions = {"max_tokens": 77}

        _ = await alchemy_provider.stream_alchemy_openai_completions(model, context, options)

        assert fake_module.captured_model is not None
        assert fake_module.captured_model["reasoning"] == "high"

    _run(_scenario())


def test_alchemy_provider_infers_minimax_api_from_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _scenario() -> None:
        final_message = _assistant_message("hello")
        done_event: AssistantMessageEvent = {
            "type": "done",
            "reason": "stop",
            "message": final_message,
        }
        fake_module = FakeAlchemyModule(FakeHandle([done_event], final_message))
        monkeypatch.setattr(alchemy_provider, "_ALCHEMY_MODULE", fake_module)

        model = Model(provider="minimax", id="MiniMax-M2.5", api="")
        context = Context(
            system_prompt="Be concise.",
            messages=[{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
        )

        _ = await alchemy_provider.stream_alchemy_openai_completions(model, context, {})

        assert fake_module.captured_model is not None
        assert fake_module.captured_model["provider"] == "minimax"
        assert fake_module.captured_model["api"] == "minimax-completions"

    _run(_scenario())


def test_alchemy_provider_explicit_api_override_is_forwarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _scenario() -> None:
        final_message = _assistant_message("hello")
        done_event: AssistantMessageEvent = {
            "type": "done",
            "reason": "stop",
            "message": final_message,
        }
        fake_module = FakeAlchemyModule(FakeHandle([done_event], final_message))
        monkeypatch.setattr(alchemy_provider, "_ALCHEMY_MODULE", fake_module)

        model = Model(
            provider="minimax",
            id="MiniMax-M2.5",
            api="openai-completions",
        )
        context = Context(
            system_prompt="Be concise.",
            messages=[{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
        )

        _ = await alchemy_provider.stream_alchemy_openai_completions(model, context, {})

        assert fake_module.captured_model is not None
        assert fake_module.captured_model["provider"] == "minimax"
        assert fake_module.captured_model["api"] == "openai-completions"

    _run(_scenario())


def test_alchemy_provider_legacy_openrouter_api_alias_maps_to_openai_completions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _scenario() -> None:
        final_message = _assistant_message("hello")
        done_event: AssistantMessageEvent = {
            "type": "done",
            "reason": "stop",
            "message": final_message,
        }
        fake_module = FakeAlchemyModule(FakeHandle([done_event], final_message))
        monkeypatch.setattr(alchemy_provider, "_ALCHEMY_MODULE", fake_module)

        model = Model(provider="openrouter", id="moonshotai/kimi-k2.5", api="openrouter")
        context = Context(
            system_prompt="Be concise.",
            messages=[{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
        )

        _ = await alchemy_provider.stream_alchemy_openai_completions(model, context, {})

        assert fake_module.captured_model is not None
        assert fake_module.captured_model["provider"] == "openrouter"
        assert fake_module.captured_model["api"] == "openai-completions"

    _run(_scenario())


def test_alchemy_provider_rejects_missing_usage_in_final_message() -> None:
    async def _scenario() -> None:
        bad_final: dict[str, object] = {
            "role": "assistant",
            "content": [{"type": "text", "text": "oops"}],
            "stop_reason": "complete",
        }
        response = alchemy_provider.AlchemyStreamResponse(_handle=FakeHandle([], bad_final))

        with pytest.raises(RuntimeError, match="usage"):
            await response.result()

    _run(_scenario())


def test_agent_preserves_usage_and_metadata_from_stream_function() -> None:
    async def _scenario() -> None:
        final_message = _assistant_message("agent contract")
        captured: dict[str, object] = {}

        async def fake_stream_fn(
            model: Model,
            context: Context,
            options: SimpleStreamOptions,
        ) -> FakeStreamResponse:
            captured["model"] = model
            captured["context"] = context
            captured["options"] = dict(options)

            partial: AssistantMessage = {
                "role": "assistant",
                "content": [{"type": "text", "text": ""}],
                "stop_reason": "complete",
                "api": final_message["api"],
                "provider": final_message["provider"],
                "model": final_message["model"],
                "usage": final_message["usage"],
            }
            events: list[AssistantMessageEvent] = [
                {"type": "start", "partial": partial},
                {
                    "type": "done",
                    "reason": "stop",
                    "message": final_message,
                    "partial": final_message,
                },
            ]
            return FakeStreamResponse(events, final_message)

        agent = Agent(AgentOptions(stream_fn=fake_stream_fn))
        agent.set_model(
            Model(
                provider="openrouter",
                id="moonshotai/kimi-k2.5",
                api="openai-completions",
            )
        )

        message = await agent.prompt("hello")
        assistant_message = cast(AssistantMessage, message)

        assert assistant_message["role"] == "assistant"
        assert assistant_message["usage"] == _usage_payload()
        assert assistant_message["provider"] == "openrouter"
        assert assistant_message["api"] == "openai-completions"

        context = cast(Context, captured["context"])
        assert context.messages[-1]["role"] == "user"

    _run(_scenario())


def test_agent_does_not_continue_turn_when_tool_execution_returns_no_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _scenario() -> None:
        call_count = 0

        async def fake_execute_tool_calls(
            tools: list[AgentTool] | None,
            assistant_message: AssistantMessage,
            signal: asyncio.Event | None,
            stream: object,
            get_steering_messages: Any = None,
        ) -> dict[str, object]:
            return {"tool_results": [], "steering_messages": None}

        agent_loop_module = importlib.import_module("tinyagent.agent_loop")
        monkeypatch.setattr(agent_loop_module, "execute_tool_calls", fake_execute_tool_calls)

        tool_call_message: AssistantMessage = {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_call",
                    "id": "call_1",
                    "name": "echo",
                    "arguments": {"text": "hello"},
                }
            ],
            "stop_reason": "tool_calls",
            "api": "openai-completions",
            "provider": "openrouter",
            "model": "moonshotai/kimi-k2.5",
            "usage": _usage_payload(),
            "timestamp": 123,
        }

        async def fake_stream_fn(
            model: Model,
            context: Context,
            options: SimpleStreamOptions,
        ) -> FakeStreamResponse:
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise AssertionError("stream_fn should be called exactly once")
            events: list[AssistantMessageEvent] = [
                {
                    "type": "done",
                    "reason": "tool_calls",
                    "message": tool_call_message,
                }
            ]
            return FakeStreamResponse(events, tool_call_message)

        agent = Agent(AgentOptions(stream_fn=fake_stream_fn))
        agent.set_model(
            Model(
                provider="openrouter",
                id="moonshotai/kimi-k2.5",
                api="openai-completions",
            )
        )

        message = await agent.prompt("hello")
        assistant_message = cast(AssistantMessage, message)

        assert call_count == 1
        assert assistant_message["stop_reason"] == "tool_calls"
        assert not any(
            isinstance(msg, dict) and msg.get("role") == "tool_result"
            for msg in agent.state["messages"]
        )

    _run(_scenario())


def test_process_turn_does_not_double_poll_steering_after_tool_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _scenario() -> None:
        steering_poll_count = 0

        async def get_steering_messages() -> list[AgentMessage]:
            nonlocal steering_poll_count
            steering_poll_count += 1
            return []

        assistant_message: AssistantMessage = {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_call",
                    "id": "call_1",
                    "name": "echo",
                    "arguments": {"text": "hello"},
                }
            ],
            "stop_reason": "tool_calls",
            "api": "openai-completions",
            "provider": "openrouter",
            "model": "moonshotai/kimi-k2.5",
            "usage": _usage_payload(),
            "timestamp": 123,
        }
        tool_result_message = {
            "role": "tool_result",
            "tool_call_id": "call_1",
            "tool_name": "echo",
            "content": [{"type": "text", "text": "ok"}],
            "details": {},
            "is_error": False,
            "timestamp": 456,
        }

        agent_loop_module = importlib.import_module("tinyagent.agent_loop")

        async def fake_stream_assistant_response(
            context: AgentContext,
            config: AgentLoopConfig,
            signal: asyncio.Event | None,
            stream: object,
            stream_fn: object = None,
        ) -> AssistantMessage:
            return assistant_message

        async def fake_execute_tool_calls(
            tools: list[AgentTool] | None,
            assistant_message: AssistantMessage,
            signal: asyncio.Event | None,
            stream: object,
            get_steering_messages_cb: Any = None,
        ) -> dict[str, object]:
            assert get_steering_messages_cb is not None
            await get_steering_messages_cb()
            return {"tool_results": [tool_result_message], "steering_messages": None}

        monkeypatch.setattr(
            agent_loop_module,
            "stream_assistant_response",
            fake_stream_assistant_response,
        )
        monkeypatch.setattr(agent_loop_module, "execute_tool_calls", fake_execute_tool_calls)

        config = AgentLoopConfig(
            model=Model(
                provider="openrouter",
                id="moonshotai/kimi-k2.5",
                api="openai-completions",
            ),
            convert_to_llm=lambda messages: cast(Any, []),
            get_steering_messages=get_steering_messages,
        )
        current_context = AgentContext(system_prompt="", messages=[], tools=[])
        stream = agent_loop_module.create_agent_stream()
        new_messages: list[dict[str, object]] = []

        turn_result = await agent_loop_module._process_turn(
            current_context,
            cast(Any, new_messages),
            [],
            config,
            None,
            stream,
            True,
            None,
            get_steering_messages,
        )

        assert steering_poll_count == 1
        assert turn_result.pending_messages == []
        assert turn_result.has_more_tool_calls is True

    _run(_scenario())
