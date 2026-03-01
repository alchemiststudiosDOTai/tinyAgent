"""Prompt caching utilities for Anthropic-style cache_control breakpoints."""

from __future__ import annotations

import asyncio

from .agent_types import AgentMessage, CacheControl, TextContent, UserMessage

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
    1. The system prompt's content blocks (handled at the Context level,
       not here -- system prompt is a plain string, so the provider must
       handle wrapping it into a structured block with cache_control).
    2. Each user message’s final content block with
       cache_control: {"type": "ephemeral"}.

    Matches the TransformContextFn signature.
    """
    return _annotate_user_messages(messages)
