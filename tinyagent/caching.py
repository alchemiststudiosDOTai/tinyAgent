"""Prompt caching utilities for Anthropic-style cache_control breakpoints."""

from __future__ import annotations

import asyncio
import copy
from typing import cast

from .agent_types import AgentMessage, CacheControl, UserMessage

EPHEMERAL_CACHE: CacheControl = {"type": "ephemeral"}


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
        if msg.get("role") != "user":
            continue

        content = msg.get("content")
        if not isinstance(content, list) or not content:
            continue

        last_block = content[-1]
        if not isinstance(last_block, dict):
            continue

        # Avoid mutating the original structures.
        annotated_block = copy.copy(last_block)
        annotated_block["cache_control"] = EPHEMERAL_CACHE

        new_content = list(content)
        new_content[-1] = annotated_block

        new_messages[i] = cast(UserMessage, {**msg, "content": new_content})
        changed = True

    return new_messages if changed else messages


async def add_cache_breakpoints(
    messages: list[AgentMessage],
    signal: asyncio.Event | None = None,
) -> list[AgentMessage]:
    """Transform function that adds cache_control breakpoints.

    Annotates:
    1. The system prompt's content blocks (handled at the Context level,
       not here -- system prompt is a plain string, so the provider must
       handle wrapping it into a structured block with cache_control).
    2. Each user message’s final content block with
       cache_control: {"type": "ephemeral"}.

    Matches the TransformContextFn signature.
    """
    return _annotate_user_messages(messages)
