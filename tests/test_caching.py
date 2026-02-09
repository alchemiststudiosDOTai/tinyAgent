"""Tests for prompt caching pipeline."""

from __future__ import annotations

import asyncio

import pytest

from tinyagent.agent_types import (
    AgentMessage,
    AssistantMessage,
    Context,
    TextContent,
    UserMessage,
)
from tinyagent.caching import add_cache_breakpoints
from tinyagent.openrouter_provider import (
    _any_block_has_cache_control,
    _build_usage_dict,
    _context_has_cache_control,
    _convert_user_message,
    _is_anthropic_model,
)


# -- add_cache_breakpoints tests --


@pytest.mark.asyncio
async def test_cache_breakpoints_annotates_last_user_message() -> None:
    """Only the last user message's final block gets cache_control."""
    messages: list[AgentMessage] = [
        {"role": "user", "content": [{"type": "text", "text": "first user msg"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "reply"}]},
        {"role": "user", "content": [{"type": "text", "text": "second user msg"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "reply 2"}]},
        {"role": "user", "content": [{"type": "text", "text": "third user msg"}]},
    ]

    result = await add_cache_breakpoints(messages)

    # First two user messages should NOT have cache_control
    first_user = result[0]
    assert first_user.get("role") == "user"
    first_content = first_user.get("content", [])
    assert "cache_control" not in first_content[0]

    second_user = result[2]
    assert second_user.get("role") == "user"
    second_content = second_user.get("content", [])
    assert "cache_control" not in second_content[0]

    # Last user message SHOULD have cache_control
    last_user = result[4]
    assert last_user.get("role") == "user"
    last_content = last_user.get("content", [])
    assert last_content[0].get("cache_control") == {"type": "ephemeral"}


@pytest.mark.asyncio
async def test_cache_breakpoints_does_not_mutate_original() -> None:
    """add_cache_breakpoints should not mutate the original messages."""
    original_content: list[TextContent] = [{"type": "text", "text": "hello"}]
    messages: list[AgentMessage] = [
        {"role": "user", "content": original_content},
    ]

    result = await add_cache_breakpoints(messages)

    # Original should be untouched
    assert "cache_control" not in original_content[0]
    # Result should have it
    assert result[0]["content"][-1].get("cache_control") == {"type": "ephemeral"}


@pytest.mark.asyncio
async def test_cache_breakpoints_empty_messages() -> None:
    """Empty message list should return empty."""
    result = await add_cache_breakpoints([])
    assert result == []


@pytest.mark.asyncio
async def test_cache_breakpoints_no_user_messages() -> None:
    """If no user messages, return unchanged."""
    messages: list[AgentMessage] = [
        {"role": "assistant", "content": [{"type": "text", "text": "hi"}]},
    ]
    result = await add_cache_breakpoints(messages)
    assert len(result) == 1
    assert result[0].get("role") == "assistant"


# -- OpenRouter helpers tests --


def test_is_anthropic_model() -> None:
    assert _is_anthropic_model("anthropic/claude-3.5-sonnet") is True
    assert _is_anthropic_model("anthropic/claude-3-opus") is True
    assert _is_anthropic_model("openai/gpt-4") is False
    assert _is_anthropic_model("google/gemini-pro") is False
    assert _is_anthropic_model("Claude-Instant") is True


def test_any_block_has_cache_control() -> None:
    blocks_with: list[TextContent] = [
        {"type": "text", "text": "hi", "cache_control": {"type": "ephemeral"}},
    ]
    blocks_without: list[TextContent] = [
        {"type": "text", "text": "hi"},
    ]
    assert _any_block_has_cache_control(blocks_with) is True
    assert _any_block_has_cache_control(blocks_without) is False


def test_convert_user_message_plain() -> None:
    """Without cache_control, content is a joined string."""
    msg: UserMessage = {
        "role": "user",
        "content": [{"type": "text", "text": "hello"}],
    }
    result = _convert_user_message(msg)
    assert result["content"] == "hello"
    assert isinstance(result["content"], str)


def test_convert_user_message_with_cache_control() -> None:
    """With cache_control, content is a list of structured dicts."""
    msg: UserMessage = {
        "role": "user",
        "content": [
            {"type": "text", "text": "hello", "cache_control": {"type": "ephemeral"}},
        ],
    }
    result = _convert_user_message(msg)
    assert isinstance(result["content"], list)
    block = result["content"][0]
    assert block["type"] == "text"
    assert block["text"] == "hello"
    assert block["cache_control"] == {"type": "ephemeral"}


def test_context_has_cache_control_true() -> None:
    ctx = Context(
        system_prompt="test",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "hi", "cache_control": {"type": "ephemeral"}},
                ],
            }
        ],
    )
    assert _context_has_cache_control(ctx) is True


def test_context_has_cache_control_false() -> None:
    ctx = Context(
        system_prompt="test",
        messages=[
            {"role": "user", "content": [{"type": "text", "text": "hi"}]},
        ],
    )
    assert _context_has_cache_control(ctx) is False


def test_build_usage_dict_with_cache_fields() -> None:
    usage = {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "cache_creation_input_tokens": 80,
        "cache_read_input_tokens": 20,
    }
    result = _build_usage_dict(usage)
    assert result["input"] == 100
    assert result["output"] == 50
    assert result["cacheWrite"] == 80
    assert result["cacheRead"] == 20
    assert result["totalTokens"] == 150


def test_build_usage_dict_without_cache_fields() -> None:
    usage = {
        "prompt_tokens": 100,
        "completion_tokens": 50,
    }
    result = _build_usage_dict(usage)
    assert result["cacheRead"] == 0
    assert result["cacheWrite"] == 0


def test_build_usage_dict_with_prompt_tokens_details() -> None:
    usage = {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "prompt_tokens_details": {"cached_tokens": 30},
    }
    result = _build_usage_dict(usage)
    assert result["cacheRead"] == 30
