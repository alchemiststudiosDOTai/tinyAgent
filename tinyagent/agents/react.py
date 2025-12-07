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
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Final

from openai import AsyncOpenAI

from ..core.exceptions import StepLimitReached
from ..core.finalizer import Finalizer
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
        Examples: ``gpt-4``, ``anthropic/claude-3.5-haiku``, ``meta-llama/llama-3.2-3b-instruct``
    api_key
        Optional OpenAI key; falls back to ``OPENAI_API_KEY`` env var.
    prompt_file
        Optional path to a text file containing the system prompt.
        If provided, will load prompt from file. Falls back to default prompt if file loading fails.
    temperature
        Temperature for LLM responses. Default ``0.7``.
    """

    tools: Sequence[Tool]
    model: str = "gpt-4o-mini"
    api_key: str | None = None
    prompt_file: str | None = None
    temperature: float = 0.7

    def __post_init__(self) -> None:
        super().__post_init__()

        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        base_prompt = get_prompt_fallback(SYSTEM, self.prompt_file)

        self._system_prompt: str = base_prompt.format(
            tools="\n".join(
                f"- {t.name}: {t.doc or '<no description>'} | args={t.signature}"
                for t in self._tool_map.values()
            )
        )

    # ------------------------------------------------------------------
    async def run(
        self,
        question: str,
        *,
        max_steps: int = MAX_STEPS,
        verbose: bool = False,
        return_result: bool = False,
    ) -> str | RunResult:
        """
        Execute the loop and return the final answer or raise StepLimitReached.

        Parameters
        ----------
        question
            The question to answer
        max_steps
            Maximum number of reasoning steps
        verbose
            If True, print detailed execution logs
        return_result
            If True, return RunResult with metadata; if False, return string (default)
        """
        start_time = time.time()
        finalizer = Finalizer()
        steps_taken = 0

        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": question},
        ]
        temperature = self.temperature

        self.logger.verbose = verbose

        self.logger.banner("REACT AGENT STARTING")
        self.logger.labeled("TASK", question)
        self.logger.labeled("SYSTEM PROMPT", self._system_prompt)
        self.logger.labeled("AVAILABLE TOOLS", str(list(self._tool_map.keys())))

        for step in range(max_steps):
            steps_taken = step + 1
            self.logger.step_header(steps_taken, max_steps)
            self.logger.messages_preview(messages)

            assistant_reply = await self._chat(messages, temperature)

            self.logger.llm_response(assistant_reply)

            payload = self._try_parse_json(assistant_reply)

            if payload is None:
                self.logger.error("JSON PARSE ERROR: Invalid JSON format")
                messages += [
                    {"role": "assistant", "content": assistant_reply},
                    {"role": "user", "content": BAD_JSON},
                ]
                temperature += TEMP_STEP
                continue

            if "scratchpad" in payload:
                self.logger.scratchpad(payload["scratchpad"])
                messages += [
                    {"role": "assistant", "content": assistant_reply},
                    {"role": "user", "content": f"Scratchpad noted: {payload['scratchpad']}"},
                ]
                del payload["scratchpad"]
                if "answer" not in payload and "tool" not in payload:
                    temperature += TEMP_STEP
                    continue

            if "answer" in payload:
                answer_value = str(payload["answer"])
                finalizer.set(answer_value, source="normal")

                self.logger.final_answer(answer_value)

                if return_result:
                    duration = time.time() - start_time
                    return RunResult(
                        output=answer_value,
                        final_answer=finalizer.get(),
                        state="completed",
                        steps_taken=steps_taken,
                        duration_seconds=duration,
                    )
                return answer_value

            name = payload.get("tool")
            args = payload.get("arguments", {}) or {}
            if name not in self._tool_map:
                return f"Unknown tool '{name}'."

            self.logger.tool_call(name, args)

            ok, result = await self._safe_tool(name, args)
            tag = "Observation" if ok else "Error"
            result_str = str(result)
            short = (result_str[:MAX_OBS_LEN] + "...") if len(result_str) > MAX_OBS_LEN else result

            truncated_from = len(result_str) if len(result_str) > MAX_OBS_LEN else None
            self.logger.tool_observation(str(short), is_error=not ok, truncated_from=truncated_from)

            messages += [
                {"role": "assistant", "content": assistant_reply},
                {"role": "user", "content": f"{tag}: {short}"},
            ]

        self.logger.final_attempt_header()

        final_try = await self._chat(
            messages + [{"role": "user", "content": "Return your best final answer now."}],
            0,
        )
        payload = self._try_parse_json(final_try) or {}
        duration = time.time() - start_time

        if "answer" in payload:
            answer_value = str(payload["answer"])
            finalizer.set(answer_value, source="final_attempt")

            self.logger.final_answer(answer_value)

            if return_result:
                return RunResult(
                    output=answer_value,
                    final_answer=finalizer.get(),
                    state="step_limit_reached",
                    steps_taken=steps_taken,
                    duration_seconds=duration,
                )
            return answer_value

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

    # ------------------------------------------------------------------
    async def _chat(self, messages: list[dict[str, str]], temperature: float) -> str:
        """Single LLM call; OpenAI-compatible."""
        self.logger.api_call(self.model, temperature)
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        content = response.choices[0].message.content or ""
        self.logger.api_response(len(content))
        return content.strip()

    @staticmethod
    def _try_parse_json(text: str) -> dict[str, Any] | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    async def _safe_tool(self, name: str, args: dict[str, Any]) -> tuple[bool, Any]:
        """
        Execute tool with argument validation.

        Returns (success: bool, result: Any)
        """
        tool = self._tool_map[name]

        from inspect import signature

        try:
            signature(tool.fn).bind(**args)
        except TypeError as exc:
            self.logger.tool_error("ARGUMENT ERROR", str(exc))
            return False, f"ArgError: {exc}"

        try:
            self.logger.tool_executing(name, args)
            result = await tool.run(args)
            self.logger.tool_result(str(result))
            return True, result
        except Exception as exc:  # pragma: no cover
            self.logger.tool_error("TOOL ERROR", str(exc))
            return False, f"ToolError: {exc}"
