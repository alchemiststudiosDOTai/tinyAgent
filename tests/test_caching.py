"""Tests for prompt caching pipeline."""

from __future__ import annotations

from typing import cast

import pytest

from tinyagent.agent_types import AgentMessage, Context, TextContent, UserMessage
from tinyagent.caching import add_cache_breakpoints
from tinyagent.openrouter_provider import (
    _any_block_has_cache_control,
    _build_usage_dict,
    _context_has_cache_control,
    _convert_user_message,
)

# -- add_cache_breakpoints tests --


@pytest.mark.asyncio
async def test_cache_breakpoints_annotates_all_user_messages() -> None:
    """All user messages' final blocks get cache_control.

    This keeps cache breakpoints stable across turns (so earlier user messages
    keep matching the cached prefix written in prior turns).
    """

    messages: list[AgentMessage] = cast(
        list[AgentMessage],
        [
            {"role": "user", "content": [{"type": "text", "text": "first user msg"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "reply"}]},
            {"role": "user", "content": [{"type": "text", "text": "second user msg"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "reply 2"}]},
            {"role": "user", "content": [{"type": "text", "text": "third user msg"}]},
        ],
    )

    result = await add_cache_breakpoints(messages)

    # All user messages should have cache_control on the last block
    for idx in (0, 2, 4):
        user_msg = cast(UserMessage, result[idx])
        assert user_msg["role"] == "user"
        content = user_msg["content"]
        assert content[-1].get("cache_control") == {"type": "ephemeral"}


@pytest.mark.asyncio
async def test_cache_breakpoints_does_not_mutate_original() -> None:
    """add_cache_breakpoints should not mutate the original messages."""
    original_content: list[TextContent] = [{"type": "text", "text": "hello"}]
    messages: list[AgentMessage] = cast(
        list[AgentMessage],
        [
            {"role": "user", "content": original_content},
        ],
    )

    result = await add_cache_breakpoints(messages)

    # Original should be untouched
    assert "cache_control" not in original_content[0]
    # Result should have it
    user_msg = cast(UserMessage, result[0])
    assert user_msg["content"][-1].get("cache_control") == {"type": "ephemeral"}


@pytest.mark.asyncio
async def test_cache_breakpoints_empty_messages() -> None:
    """Empty message list should return empty."""
    result = await add_cache_breakpoints([])
    assert result == []


@pytest.mark.asyncio
async def test_cache_breakpoints_no_user_messages() -> None:
    """If no user messages, return unchanged."""
    messages: list[AgentMessage] = cast(
        list[AgentMessage],
        [
            {"role": "assistant", "content": [{"type": "text", "text": "hi"}]},
        ],
    )
    result = await add_cache_breakpoints(messages)
    assert len(result) == 1
    assert result[0].get("role") == "assistant"


# -- OpenRouter helpers tests --


def test_any_block_has_cache_control() -> None:
    blocks_with: list[TextContent | dict[str, object]] = [
        {"type": "text", "text": "hi", "cache_control": {"type": "ephemeral"}},
    ]
    blocks_without: list[TextContent | dict[str, object]] = [
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
    usage: dict[str, object] = {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "cache_creation_input_tokens": 80,
        "cache_read_input_tokens": 20,
    }
    result = _build_usage_dict(usage)
    assert result["input"] == 100
    assert result["output"] == 50
    assert result["cache_write"] == 80
    assert result["cache_read"] == 20
    assert result["total_tokens"] == 150


def test_build_usage_dict_without_cache_fields() -> None:
    usage: dict[str, object] = {
        "prompt_tokens": 100,
        "completion_tokens": 50,
    }
    result = _build_usage_dict(usage)
    assert result["cache_read"] == 0
    assert result["cache_write"] == 0


def test_build_usage_dict_with_prompt_tokens_details() -> None:
    usage: dict[str, object] = {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "prompt_tokens_details": {"cached_tokens": 30, "cache_write_tokens": 11},
    }
    result = _build_usage_dict(usage)
    assert result["cache_read"] == 30
    assert result["cache_write"] == 11


def test_build_usage_dict_prefers_provider_total_tokens() -> None:
    usage: dict[str, object] = {
        "prompt_tokens": 79,
        "completion_tokens": 114,
        "completion_tokens_details": {"reasoning_tokens": 91},
        "total_tokens": 193,
    }
    result = _build_usage_dict(usage)
    assert result["input"] == 79
    assert result["output"] == 114
    assert result["total_tokens"] == 193


def test_build_usage_dict_total_tokens_fallback_when_invalid() -> None:
    usage: dict[str, object] = {
        "prompt_tokens": 40,
        "completion_tokens": 8,
        "total_tokens": "invalid",
    }
    result = _build_usage_dict(usage)
    assert result["total_tokens"] == 48


def test_build_usage_dict_prefers_explicit_cache_fields_over_prompt_details() -> None:
    usage: dict[str, object] = {
        "prompt_tokens": 100,
        "completion_tokens": 25,
        "cache_read_input_tokens": 12,
        "cache_creation_input_tokens": 9,
        "prompt_tokens_details": {"cached_tokens": 7, "cache_write_tokens": 5},
    }
    result = _build_usage_dict(usage)
    assert result["cache_read"] == 12
    assert result["cache_write"] == 9
