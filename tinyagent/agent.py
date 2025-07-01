"""
tinyagent.agent
Minimal, typed ReAct agent (Reason + Act) with JSON-tool calling.

Public surface
--------------
ReactAgent  – class
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Final

from openai import OpenAI

from .prompt import BAD_JSON, SYSTEM  # prompt.py holds the two template strings
from .tools import Tool, get_registry  # our Tool wrapper and registry

__all__ = ["ReactAgent"]

# ---------------------------------------------------------------------------
MAX_STEPS: Final = 10
TEMP_STEP: Final = 0.2


class StepLimitReached(RuntimeError):
    """Raised when no answer is produced within MAX_STEPS."""


@dataclass(kw_only=True)
class ReactAgent:
    """
    A lightweight ReAct loop.

    Parameters
    ----------
    tools
        Sequence of Tool objects (typically produced by @tool decorator).
    model
        Model name (OpenAI or OpenRouter format). Default ``gpt-4o-mini``.
        Examples: ``gpt-4``, ``anthropic/claude-3.5-haiku``, ``meta-llama/llama-3.2-3b-instruct``
    api_key
        Optional OpenAI key; falls back to ``OPENAI_API_KEY`` env var.
    """

    tools: Sequence[Tool]
    model: str = "gpt-4o-mini"
    api_key: str | None = None

    # ------------------------------------------------------------------
    def __post_init__(self) -> None:
        if not self.tools:
            raise ValueError("ReactAgent requires at least one tool.")

        # Get the registry to look up Tool objects for functions
        registry = get_registry()

        # Build tool map, handling both Tool objects and functions
        self._tool_map: dict[str, Tool] = {}
        for item in self.tools:
            if isinstance(item, Tool):
                self._tool_map[item.name] = item
            elif callable(item) and item.__name__ in registry:
                # Function decorated with @tool
                self._tool_map[item.__name__] = registry[item.__name__]
            else:
                raise ValueError(f"Invalid tool: {item}")

        # Initialize OpenAI client
        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        self.client = OpenAI(api_key=api_key, base_url=base_url)

        # Render immutable system prompt once
        self._system_prompt: str = SYSTEM.format(
            tools="\n".join(
                f"- {t.name}: {t.doc or '<no description>'} | args={t.signature}"
                for t in self._tool_map.values()
            )
        )

    # ------------------------------------------------------------------
    def run(self, question: str, *, max_steps: int = MAX_STEPS) -> str:
        """
        Execute the loop and return the final answer or raise StepLimitReached.
        """
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": question},
        ]
        temperature = 0.0

        for _ in range(max_steps):
            assistant_reply = self._chat(messages, temperature)
            payload = self._try_parse_json(assistant_reply)

            # If JSON malformed → ask model to fix
            if payload is None:
                messages += [
                    {"role": "assistant", "content": assistant_reply},
                    {"role": "user", "content": BAD_JSON},
                ]
                temperature += TEMP_STEP
                continue

            # Final answer path
            if "answer" in payload:
                return str(payload["answer"])

            # Tool invocation path
            name = payload.get("tool")
            args = payload.get("arguments", {}) or {}
            if name not in self._tool_map:
                return f"Unknown tool '{name}'."

            result = self._safe_tool(name, args)
            messages += [
                {"role": "assistant", "content": assistant_reply},
                {"role": "user", "content": f"Tool '{name}' returned: {result}"},
            ]

        raise StepLimitReached("Exceeded max ReAct steps without an answer.")

    # ------------------------------------------------------------------
    def _chat(self, messages: list[dict[str, str]], temperature: float) -> str:
        """Single LLM call; OpenAI-compatible."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()

    @staticmethod
    def _try_parse_json(text: str) -> dict[str, Any] | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def _safe_tool(self, name: str, args: dict[str, Any]) -> str:
        try:
            return self._tool_map[name].run(args)
        except Exception as exc:  # pragma: no cover
            return f"Error in tool '{name}': {exc}"
