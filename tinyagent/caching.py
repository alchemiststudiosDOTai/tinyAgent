"""Prompt caching utilities for Anthropic-style cache_control breakpoints."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import cast

from .agent_types import (
    ZERO_USAGE,
    AgentMessage,
    CacheControl,
    Context,
    JsonObject,
    TextContent,
    UserMessage,
)

EPHEMERAL_CACHE = CacheControl(type="ephemeral")


def _annotate_user_messages(messages: list[AgentMessage]) -> list[AgentMessage]:
    """Annotate each user message's final content block with cache_control.

    This is intentionally applied to *all* user messages (not just the last one)
    so that cache breakpoints remain stable across turns.

    If we only annotate the last user message, then on the next turn that same
    message moves earlier in the history and would lose its cache_control marker,
    which changes the serialized prompt prefix and prevents cache hits.
    """

    changed = False
    new_messages = list(messages)

    for i, msg in enumerate(messages):
        if not isinstance(msg, UserMessage):
            continue
        if not msg.content:
            continue

        last_block = msg.content[-1]
        if not isinstance(last_block, TextContent):
            continue

        # Avoid mutating the original structures.
        annotated_block = last_block.model_copy(deep=True)
        annotated_block.cache_control = EPHEMERAL_CACHE.model_copy(deep=True)

        new_content = list(msg.content)
        new_content[-1] = annotated_block

        updated_message = msg.model_copy(deep=True)
        updated_message.content = new_content

        new_messages[i] = updated_message
        changed = True

    return new_messages if changed else messages


async def add_cache_breakpoints(
    messages: list[AgentMessage],
    signal: asyncio.Event | None = None,
) -> list[AgentMessage]:
    """Transform function that adds cache_control breakpoints.

    Annotates:
    1. The system prompt’s content blocks (handled at the Context level,
       not here -- system prompt is a plain string, so the provider must
       handle wrapping it into a structured block with cache_control).
    2. Each user message’s final content block with
       cache_control: {"type": "ephemeral"}.

    Matches the TransformContextFn signature.
    """
    return _annotate_user_messages(messages)


def _any_block_has_cache_control(blocks: Sequence[object]) -> bool:
    """Check if any content block carries a cache_control directive."""
    for block in blocks:
        if isinstance(block, TextContent) and block.cache_control is not None:
            return True
        if isinstance(block, dict) and block.get("cache_control") is not None:
            return True
    return False


def _context_has_cache_control(context: Context) -> bool:
    """Check if any message in the context has cache_control on a text block."""
    for msg in context.messages:
        content = (
            cast(list[object], msg.get("content", []))
            if isinstance(msg, dict)
            else cast(list[object], msg.content)
        )
        for block in content:
            if isinstance(block, TextContent) and block.cache_control is not None:
                return True
            if isinstance(block, dict) and block.get("cache_control") is not None:
                return True
    return False


def _extract_text_from_block(block: object) -> str | None:
    """Extract text value from a TextContent model or dict."""
    if isinstance(block, TextContent):
        return block.text if isinstance(block.text, str) else None
    if isinstance(block, dict) and block.get("type") == "text":
        text_val = block.get("text")
        return text_val if isinstance(text_val, str) else None
    return None


def _convert_block_to_structured(block: object) -> dict[str, object] | None:
    """Convert a single block to structured format with cache_control."""
    if isinstance(block, TextContent):
        entry: dict[str, object] = {"type": "text", "text": block.text or ""}
        if block.cache_control is not None:
            entry["cache_control"] = block.cache_control.model_dump(exclude_none=True)
        return entry
    if isinstance(block, dict) and block.get("type") == "text":
        entry = {"type": "text", "text": block.get("text", "")}
        cache_control = block.get("cache_control")
        if cache_control is not None:
            entry["cache_control"] = cache_control
        return entry
    return None


def _convert_blocks_structured(content: list[object]) -> list[dict[str, object]]:
    """Convert content blocks to structured format preserving cache_control."""
    result: list[dict[str, object]] = []
    for block in content:
        structured = _convert_block_to_structured(block)
        if structured is not None:
            result.append(structured)
    return result


def _extract_text_parts(content: list[object]) -> list[str]:
    """Extract text parts from content blocks."""
    text_parts: list[str] = []
    for block in content:
        text = _extract_text_from_block(block)
        if text is not None:
            text_parts.append(text)
    return text_parts


def _convert_user_message(msg: UserMessage) -> dict[str, object]:
    """Convert a UserMessage to OpenAI-compatible dict format."""
    content: list[object] = (
        cast(list[object], msg.get("content", []))
        if isinstance(msg, dict)
        else cast(list[object], msg.content)
    )
    if _any_block_has_cache_control(content):
        return {"role": "user", "content": _convert_blocks_structured(content)}
    return {"role": "user", "content": "\n".join(_extract_text_parts(content))}


def _build_usage_dict(usage: dict[str, object]) -> JsonObject:
    """Build a normalized usage dict from API response usage, including cache stats."""
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)
    cache_write = usage.get("cache_creation_input_tokens", 0)
    # OpenRouter may also use prompt_tokens_details for cache info
    details = usage.get("prompt_tokens_details")
    if isinstance(details, dict):
        if not cache_read:
            cache_read = details.get("cached_tokens", 0)
        if not cache_write:
            # OpenRouter uses `cache_write_tokens` in prompt_tokens_details.
            cache_write = details.get("cache_write_tokens", 0)

    if not isinstance(input_tokens, int | float):
        input_tokens = 0
    if not isinstance(output_tokens, int | float):
        output_tokens = 0
    if not isinstance(cache_read, int | float):
        cache_read = 0
    if not isinstance(cache_write, int | float):
        cache_write = 0

    total_tokens = usage.get("total_tokens")
    if not isinstance(total_tokens, int | float):
        total_tokens = int(input_tokens) + int(output_tokens)

    usage_copy: dict[str, object] = dict(ZERO_USAGE)
    cost = usage_copy.get("cost")
    usage_copy["cost"] = dict(cost) if isinstance(cost, dict) else {}

    normalized: JsonObject = cast(JsonObject, usage_copy)
    normalized["input"] = int(input_tokens)
    normalized["output"] = int(output_tokens)
    normalized["cache_read"] = int(cache_read)
    normalized["cache_write"] = int(cache_write)
    normalized["total_tokens"] = int(total_tokens)
    return normalized
