"""Helpers for inspecting agent message content."""

from __future__ import annotations

from ..agent_types import (
    AgentMessage,
    AssistantMessage,
    TextContent,
    ThinkingContent,
    ToolCallContent,
)


def _is_nonempty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def assistant_content_item_has_meaningful_content(item: object) -> bool:
    """Return whether an assistant content item contains meaningful content."""

    if not item:
        return False

    if isinstance(item, ThinkingContent):
        return _is_nonempty_str(item.thinking)
    if isinstance(item, TextContent):
        return _is_nonempty_str(item.text)
    if isinstance(item, ToolCallContent):
        return _is_nonempty_str(item.name)

    return False


def has_meaningful_content(partial: AgentMessage | None) -> bool:
    """Check if a partial message has meaningful content worth saving."""

    if not isinstance(partial, AssistantMessage):
        return False
    if not partial.content:
        return False

    return any(assistant_content_item_has_meaningful_content(item) for item in partial.content)
