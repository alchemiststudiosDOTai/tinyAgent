"""Shared provider contract helpers."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol, TypeAlias, cast

from pydantic import BaseModel

from .agent_types import AssistantMessage, AssistantMessageEvent, JsonObject, Model

ReasoningEffort: TypeAlias = Literal["minimal", "low", "medium", "high", "xhigh"]
ReasoningMode: TypeAlias = bool | ReasoningEffort

_USAGE_KEYS = frozenset({"input", "output", "cache_read", "cache_write", "total_tokens", "cost"})
_COST_KEYS = frozenset({"input", "output", "cache_read", "cache_write", "total"})


class BindingStreamHandle(Protocol):
    def next_event(self) -> object | None: ...

    def result(self) -> object: ...


class ProviderMetadataModel(Model):
    """Common optional model metadata accepted by binding-backed providers."""

    name: str | None = None
    headers: dict[str, str] | None = None
    context_window: int = 128_000
    max_tokens: int = 4096
    reasoning: ReasoningMode = False


@dataclass(frozen=True)
class ResolvedModelMetadata:
    name: str | None
    headers: dict[str, str] | None
    reasoning: ReasoningMode
    context_window: int | None
    max_tokens: int | None


@dataclass
class BindingStreamResponseBase(AsyncIterator[AssistantMessageEvent]):
    """Async stream adapter for binding handles with blocking methods."""

    _handle: BindingStreamHandle
    invalid_event_message: str
    _final_message: AssistantMessage | None = None

    async def result(self) -> AssistantMessage:
        if self._final_message is not None:
            return self._final_message

        raw_message = await asyncio.to_thread(self._handle.result)
        final_message = validate_assistant_message_contract(
            raw_message,
            where="result",
            require_usage=True,
        )
        self._final_message = final_message
        return final_message

    def __aiter__(self) -> BindingStreamResponseBase:
        return self

    async def __anext__(self) -> AssistantMessageEvent:
        raw_event = await asyncio.to_thread(self._handle.next_event)
        if raw_event is None:
            raise StopAsyncIteration
        if isinstance(raw_event, AssistantMessageEvent):
            return raw_event
        if not isinstance(raw_event, dict):
            raise RuntimeError(self.invalid_event_message)
        return AssistantMessageEvent.model_validate(raw_event)


def missing_keys(data: dict[str, object], required: frozenset[str]) -> list[str]:
    return sorted(key for key in required if key not in data)


def validate_usage_contract(raw_usage: object, *, where: str) -> JsonObject:
    if not isinstance(raw_usage, dict):
        raise RuntimeError(f"{where}: usage must be a dict")

    usage = cast(dict[str, object], raw_usage)
    missing_usage = missing_keys(usage, _USAGE_KEYS)
    if missing_usage:
        raise RuntimeError(f"{where}: usage missing key(s): {', '.join(missing_usage)}")

    cost_raw = usage.get("cost")
    if not isinstance(cost_raw, dict):
        raise RuntimeError(f"{where}: usage.cost must be a dict")

    cost = cast(dict[str, object], cost_raw)
    missing_cost = missing_keys(cost, _COST_KEYS)
    if missing_cost:
        raise RuntimeError(f"{where}: usage.cost missing key(s): {', '.join(missing_cost)}")

    return cast(JsonObject, usage)


def validate_assistant_message_contract(
    raw_message: object,
    *,
    where: str,
    require_usage: bool,
) -> AssistantMessage:
    if isinstance(raw_message, AssistantMessage):
        message = raw_message
    elif isinstance(raw_message, dict):
        message = AssistantMessage.model_validate(raw_message)
    else:
        raise RuntimeError(f"{where}: assistant message must be a dict")

    if require_usage:
        validate_usage_contract(message.usage, where=where)

    return message


def resolve_model_metadata(
    model: Model,
    *,
    context_window: int | None,
    max_tokens: int | None,
) -> ResolvedModelMetadata:
    if isinstance(model, ProviderMetadataModel):
        return ResolvedModelMetadata(
            name=model.name,
            headers=model.headers,
            reasoning=model.reasoning,
            context_window=model.context_window,
            max_tokens=model.max_tokens,
        )
    return ResolvedModelMetadata(
        name=None,
        headers=None,
        reasoning=False,
        context_window=context_window,
        max_tokens=max_tokens,
    )


def dump_model_payload(payload: BaseModel) -> dict[str, object]:
    return payload.model_dump(exclude_none=True)
