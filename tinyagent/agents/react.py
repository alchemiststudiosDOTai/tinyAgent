"""
tinyagent.agent
Minimal, typed ReAct agent (Reason + Act) with JSON-tool calling.

Public surface
--------------
ReactAgent  - class
"""

from __future__ import annotations

import os
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Final, Literal

from openai import AsyncOpenAI

from ..core.adapters import ToolCallingAdapter, ToolCallingMode, get_adapter
from ..core.exceptions import StepLimitReached
from ..core.finalizer import Finalizer
from ..core.memory import Memory
from ..core.registry import Tool
from ..core.types import RunResult
from ..prompts.loader import get_prompt_fallback
from ..prompts.templates import BAD_JSON, SYSTEM
from .base import BaseAgent

__all__ = ["ReactAgent"]

# ---------------------------------------------------------------------------
MAX_STEPS: Final = 10
TEMP_STEP: Final = 0.2
MAX_OBS_LEN: Final = 500
MAX_TEMPERATURE: Final = 2.0
TOOL_KEY: Final = "tool"
ARGUMENTS_KEY: Final = "arguments"
ANSWER_KEY: Final = "answer"
SCRATCHPAD_KEY: Final = "scratchpad"
VALIDATION_ERROR_FALLBACK: Final = "Tool arguments failed validation."


@dataclass(kw_only=True)
class ReactAgent(BaseAgent):
    """
    A lightweight ReAct loop.

    Parameters
    ----------
    tools
        Sequence of Tool objects
    model
        Model name (OpenAI format). Default ``gpt-4o-mini``.
    api_key
        Optional OpenAI key; falls back to ``OPENAI_API_KEY`` env var.
    prompt_file
        Optional path to a text file containing the system prompt.
    temperature
        Temperature for LLM responses. Default ``0.7``.
    max_tokens
        Maximum tokens in LLM response. Default ``None`` (model default).
    tool_calling_mode
        Tool calling adapter mode. Default ``ToolCallingMode.AUTO``.
    """

    tools: Sequence[Tool]
    model: str = "gpt-4o-mini"
    api_key: str | None = None
    prompt_file: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    tool_calling_mode: (
        ToolCallingMode | Literal["auto", "native", "structured", "validated", "parsed"]
    ) = ToolCallingMode.AUTO

    _adapter: ToolCallingAdapter = field(init=False, repr=False)
    _memory: Memory = field(init=False, repr=False)

    def __post_init__(self) -> None:
        super().__post_init__()

        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        self.tool_calling_mode = self._normalize_tool_calling_mode(self.tool_calling_mode)
        self._adapter = get_adapter(self.model, self.tool_calling_mode)
        self._memory = Memory()

        base_prompt = get_prompt_fallback(SYSTEM, self.prompt_file)
        self._system_prompt: str = base_prompt.format(
            tools="\n".join(
                f"- {t.name}: {t.doc or '<no description>'} | args={t.signature}"
                for t in self._tool_map.values()
            )
        )

    def _normalize_tool_calling_mode(self, mode: ToolCallingMode | str) -> ToolCallingMode:
        if isinstance(mode, ToolCallingMode):
            return mode
        return ToolCallingMode(mode)

    # ------------------------------------------------------------------
    async def run(
        self,
        question: str,
        *,
        max_steps: int = MAX_STEPS,
        verbose: bool = False,
        return_result: bool = False,
    ) -> str | RunResult:
        """Execute the loop and return the final answer or raise StepLimitReached."""
        start_time = time.time()
        finalizer = Finalizer()

        # Initialize
        self._memory.clear()
        self._memory.add_system(self._system_prompt)
        self._memory.add_user(question)
        temperature = self.temperature

        # Main loop
        steps_taken = 0
        for step in range(max_steps):
            steps_taken = step + 1
            result, increment_temp = await self._process_step(
                start_time, steps_taken, return_result, finalizer, temperature
            )
            if result is not None:
                return result
            if increment_temp:
                temperature = min(temperature + TEMP_STEP, MAX_TEMPERATURE)

        # Final attempt
        return await self._attempt_final_answer(start_time, steps_taken, return_result, finalizer)

    async def _process_step(
        self,
        start_time: float,
        steps_taken: int,
        return_result: bool,
        finalizer: Finalizer,
        temperature: float,
    ) -> tuple[str | RunResult | None, bool]:
        """Process a single step. Returns (result, should_increment_temp)."""
        response = await self._chat(temperature)

        payload = self._adapter.extract_tool_call(response)
        if not isinstance(payload, dict):
            self._add_error(response, BAD_JSON)
            return (None, True)

        validation = self._adapter.validate_tool_call(payload, self._tool_map)
        if not validation.is_valid:
            self._add_error(response, validation.error_message or VALIDATION_ERROR_FALLBACK)
            return (None, True)
        if validation.arguments is not None:
            payload[ARGUMENTS_KEY] = validation.arguments

        # Scratchpad only (no tool or answer) - just note it
        if SCRATCHPAD_KEY in payload and ANSWER_KEY not in payload and TOOL_KEY not in payload:
            self._memory.add(self._adapter.format_assistant_message(response))
            self._memory.add_user(f"Scratchpad noted: {payload[SCRATCHPAD_KEY]}")
            return (None, True)

        # Final answer
        if ANSWER_KEY in payload:
            return (
                self._make_result(
                    payload[ANSWER_KEY], start_time, steps_taken, return_result, finalizer, "normal"
                ),
                False,
            )

        # Tool call
        if TOOL_KEY in payload:
            return await self._execute_tool(
                payload, response, start_time, steps_taken, return_result, finalizer
            )

        return (None, True)

    def _add_error(self, response: Any, error: str) -> None:
        """Add error response to memory."""
        self._memory.add(self._adapter.format_assistant_message(response))
        self._memory.add(self._adapter.format_tool_result(None, error, is_error=True))

    async def _execute_tool(
        self,
        payload: dict[str, Any],
        response: Any,
        start_time: float,
        steps_taken: int,
        return_result: bool,
        finalizer: Finalizer,
    ) -> tuple[str | RunResult | None, bool]:
        """Execute tool and add result to memory."""
        name = payload.get(TOOL_KEY)
        args = payload.get(ARGUMENTS_KEY, {}) or {}

        if name not in self._tool_map:
            return (f"Error: Unknown tool '{name}'", False)

        ok, result = await self._safe_tool(name, args)
        result_str = str(result)
        short = (result_str[:MAX_OBS_LEN] + "...") if len(result_str) > MAX_OBS_LEN else result_str

        # Add to memory
        self._memory.add(self._adapter.format_assistant_message(response))
        self._memory.add(self._adapter.format_tool_result(None, short, is_error=not ok))

        return (None, False)

    async def _attempt_final_answer(
        self,
        start_time: float,
        steps_taken: int,
        return_result: bool,
        finalizer: Finalizer,
    ) -> str | RunResult:
        """Attempt to get a final answer after loop exhaustion."""
        self._memory.add_user("Return your best final answer now.")
        response = await self._chat(temperature=0)

        payload = self._adapter.extract_tool_call(response)
        if isinstance(payload, dict) and ANSWER_KEY in payload:
            return self._make_result(
                payload[ANSWER_KEY],
                start_time,
                steps_taken,
                return_result,
                finalizer,
                "final_attempt",
            )

        duration = time.time() - start_time
        error = StepLimitReached(
            "Exceeded max steps without an answer.",
            steps_taken=steps_taken,
            final_attempt_made=True,
        )

        if return_result:
            return RunResult(
                output="",
                final_answer=None,
                state="step_limit_reached",
                steps_taken=steps_taken,
                duration_seconds=duration,
                error=error,
            )
        raise error

    def _make_result(
        self,
        answer: Any,
        start_time: float,
        steps_taken: int,
        return_result: bool,
        finalizer: Finalizer,
        source: Literal["normal", "final_attempt"],
    ) -> str | RunResult:
        """Create result from answer."""
        answer_value = str(answer)
        finalizer.set(answer_value, source=source)

        if return_result:
            duration = time.time() - start_time
            state: Literal["completed", "step_limit_reached"] = (
                "completed" if source == "normal" else "step_limit_reached"
            )
            return RunResult(
                output=answer_value,
                final_answer=finalizer.get(),
                state=state,
                steps_taken=steps_taken,
                duration_seconds=duration,
            )
        return answer_value

    # ------------------------------------------------------------------
    async def _chat(self, temperature: float) -> Any:
        """Single LLM call. Returns raw ChatCompletion response."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": self._memory.to_list(),
            "temperature": temperature,
        }
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens

        adapter_kwargs = self._adapter.format_request(
            list(self._tool_map.values()), self._memory.to_list()
        )
        kwargs.update(adapter_kwargs)

        return await self.client.chat.completions.create(**kwargs)  # type: ignore[arg-type]

    async def _safe_tool(self, name: str, args: dict[str, Any]) -> tuple[bool, Any]:
        """Execute tool. Returns (success, result)."""
        tool = self._tool_map[name]

        from inspect import signature

        try:
            signature(tool.fn).bind(**args)
        except TypeError as exc:
            return False, f"ArgError: {exc}"

        try:
            result = await tool.run(args)
            return True, result
        except Exception as exc:
            return False, f"ToolError: {exc}"
