"""Prompt caching utilities for Anthropic-style cache_control breakpoints."""

from __future__ import annotations

import asyncio
import copy
from typing import cast

from .agent_types import AgentMessage, CacheControl, UserMessage

EPHEMERAL_CACHE: CacheControl = {"type": "ephemeral"}


def _annotate_last_user_message(messages: list[AgentMessage]) -> list[AgentMessage]:
    """Find the last user message and annotate its final content block."""
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if msg.get("role") != "user":
            continue

        content = msg.get("content")
        if not isinstance(content, list) or not content:
            continue

        last_block = content[-1]
        if not isinstance(last_block, dict):
            continue

        annotated_block = copy.copy(last_block)
        annotated_block["cache_control"] = EPHEMERAL_CACHE

        new_content = list(content)
        new_content[-1] = annotated_block

        new_msg = cast(UserMessage, {**msg, "content": new_content})
        messages = list(messages)
        messages[i] = new_msg
        return messages

    return messages


async def add_cache_breakpoints(
    messages: list[AgentMessage],
    signal: asyncio.Event | None = None,
) -> list[AgentMessage]:
    """Transform function that adds cache_control breakpoints.

    Annotates:
    1. The system prompt's content blocks (handled at the Context level,
       not here -- system prompt is a plain string, so the provider must
       handle wrapping it into a structured block with cache_control).
    2. The last user message's final content block with
       cache_control: {"type": "ephemeral"}.

    Matches the TransformContextFn signature.
    """
    return _annotate_last_user_message(messages)
