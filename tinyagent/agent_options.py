"""Agent configuration types."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeAlias

from .agent_types import (
    AgentMessage,
    AgentState,
    MaybeAwaitable,
    Message,
    StreamFn,
    ThinkingBudgets,
)

ConvertToLlmCallback: TypeAlias = Callable[[list[AgentMessage]], MaybeAwaitable[list[Message]]]
TransformContextCallback: TypeAlias = Callable[
    [list[AgentMessage], asyncio.Event | None],
    Awaitable[list[AgentMessage]],
]
ApiKeyResolverCallback: TypeAlias = Callable[[str], MaybeAwaitable[str | None]]


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
