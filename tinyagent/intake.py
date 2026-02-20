"""L1 Intake — signal capture · normalization · context enrichment.

The first layer of the orchestration spine. Accepts raw input from any source,
runs it through a configurable chain of enrichers, and produces a normalized
UserMessage with metadata that downstream layers (L2 Coordination) can use
for routing and planning decisions.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TypeAlias, Union

from .agent_types import ImageContent, TextContent, UserMessage

RawInput: TypeAlias = Union[str, list["TextContent | ImageContent"]]
Enricher: TypeAlias = Callable[["IntakeSignal"], "IntakeSignal | Awaitable[IntakeSignal]"]


@dataclass
class IntakeSignal:
    """Captured signal moving through the L1 pipeline.

    Enrichers read and write ``metadata`` and may modify ``content``.
    """

    content: list[TextContent | ImageContent]
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class IntakeResult:
    """Output of L1: a normalized UserMessage plus enrichment metadata for L2."""

    message: UserMessage
    metadata: dict[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now_ms() -> int:
    return int(asyncio.get_event_loop().time() * 1000)


async def _run_enricher(enricher: Enricher, signal: IntakeSignal) -> IntakeSignal:
    """Run a single enricher, handling both sync and async callables."""
    result = enricher(signal)
    if isinstance(result, Awaitable):
        return await result
    return result


def _capture(raw: RawInput) -> IntakeSignal:
    """Signal capture: normalize diverse raw inputs into an IntakeSignal."""
    if isinstance(raw, str):
        content: list[TextContent | ImageContent] = [{"type": "text", "text": raw}]
        return IntakeSignal(content=content)
    return IntakeSignal(content=list(raw))


def _normalize(signal: IntakeSignal) -> IntakeResult:
    """Normalization: convert an enriched signal into a UserMessage + metadata."""
    message: UserMessage = {
        "role": "user",
        "content": signal.content,
        "timestamp": _now_ms(),
    }
    return IntakeResult(message=message, metadata=dict(signal.metadata))


# ---------------------------------------------------------------------------
# Built-in enrichers
# ---------------------------------------------------------------------------


def enrich_token_estimate(signal: IntakeSignal) -> IntakeSignal:
    """Rough token count (~4 chars per token for English text)."""
    char_count = 0
    for block in signal.content:
        if block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str):
                char_count += len(text)
    signal.metadata["token_estimate"] = char_count // 4
    return signal


def enrich_input_type(signal: IntakeSignal) -> IntakeSignal:
    """Classify input as ``text``, ``image``, or ``multimodal``."""
    has_text = any(b.get("type") == "text" for b in signal.content)
    has_image = any(b.get("type") == "image" for b in signal.content)
    if has_text and has_image:
        signal.metadata["input_type"] = "multimodal"
    elif has_image:
        signal.metadata["input_type"] = "image"
    else:
        signal.metadata["input_type"] = "text"
    return signal


DEFAULT_ENRICHERS: list[Enricher] = [enrich_token_estimate, enrich_input_type]


# ---------------------------------------------------------------------------
# Intake pipeline
# ---------------------------------------------------------------------------


class Intake:
    """L1 Intake pipeline: signal capture → context enrichment → normalization.

    Accepts raw input (string or content blocks), runs it through a configurable
    chain of enrichers, and produces a normalized UserMessage with enrichment
    metadata that downstream layers (L2 Coordination) can use for routing and
    planning decisions.
    """

    def __init__(self, enrichers: list[Enricher] | None = None) -> None:
        if enrichers is not None:
            self._enrichers: list[Enricher] = list(enrichers)
        else:
            self._enrichers = list(DEFAULT_ENRICHERS)

    def add_enricher(self, enricher: Enricher) -> Intake:
        """Append an enricher to the pipeline. Returns self for chaining."""
        self._enrichers.append(enricher)
        return self

    @property
    def enrichers(self) -> list[Enricher]:
        """Current enricher chain (defensive copy)."""
        return list(self._enrichers)

    async def process(self, raw: RawInput) -> IntakeResult:
        """Run the full L1 pipeline: capture → enrich → normalize."""
        signal = _capture(raw)
        for enricher in self._enrichers:
            signal = await _run_enricher(enricher, signal)
        return _normalize(signal)
