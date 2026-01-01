"""
tinyagent.agent
Minimal, typed ReAct agent (Reason + Act) with JSON-tool calling.

Public surface
--------------
ReactAgent  - class
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Final, Literal

from openai import AsyncOpenAI

from ..core.exceptions import StepLimitReached
from ..core.finalizer import Finalizer
from ..core.registry import Tool
from ..core.types import RunResult
from ..memory import (
    ActionStep,
    MemoryManager,
    ScratchpadStep,
    SystemPromptStep,
    TaskStep,
    keep_last_n_steps,
)
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
    memory
        Optional MemoryManager instance. If None, one will be created automatically.
    enable_pruning
        If True, apply pruning strategy after each step. Default ``True``.
    prune_keep_last
        Number of recent action steps to keep when pruning. Default ``5``.
    """

    tools: Sequence[Tool]
    model: str = "gpt-4o-mini"
    api_key: str | None = None
    prompt_file: str | None = None
    temperature: float = 0.7
    memory: MemoryManager = field(default_factory=MemoryManager)
    enable_pruning: bool = True
    prune_keep_last: int = 5

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

        # Initialize run state
        temperature = self._initialize_run(question, verbose)

        # Main step loop
        for step in range(max_steps):
            steps_taken = step + 1
            result = await self._process_step(
                steps_taken, max_steps, temperature, start_time, return_result, finalizer
            )
            if result is not None:
                return result

        # Final attempt after loop exhaustion
        return await self._attempt_final_answer(start_time, steps_taken, return_result, finalizer)

    def _initialize_run(self, question: str, verbose: bool) -> float:
        """Initialize memory and logging for a new run. Returns initial temperature."""
        self.memory.clear()
        self.memory.add(SystemPromptStep(content=self._system_prompt))
        self.memory.add(TaskStep(task=question))

        self.logger.verbose = verbose
        self.logger.banner("REACT AGENT STARTING")
        self.logger.labeled("TASK", question)
        self.logger.labeled("SYSTEM PROMPT", self._system_prompt)
        self.logger.labeled("AVAILABLE TOOLS", str(list(self._tool_map.keys())))

        return self.temperature

    async def _process_step(
        self,
        step_num: int,
        max_steps: int,
        temperature: float,
        start_time: float,
        return_result: bool,
        finalizer: Finalizer,
    ) -> str | RunResult | None:
        """
        Process a single reasoning step.
        Returns None to continue loop, or a result to return immediately.
        """
        self.logger.step_header(step_num, max_steps)

        messages = self.memory.to_messages()
        self.logger.messages_preview(messages)

        assistant_reply = await self._chat(messages, temperature)
        self.logger.llm_response(assistant_reply)

        payload = self._try_parse_json(assistant_reply)
        if payload is None:
            self._handle_parse_error(assistant_reply)
            return None

        # Handle scratchpad content
        if "scratchpad" in payload:
            self._handle_scratchpad(payload, assistant_reply)
            if "answer" not in payload and "tool" not in payload:
                return None

        # Handle final answer
        if "answer" in payload:
            return self._handle_final_answer(
                payload["answer"], start_time, step_num, return_result, finalizer, "normal"
            )

        # Execute tool
        await self._execute_tool(
            payload, assistant_reply, temperature, start_time, step_num, return_result, finalizer
        )
        return None

    def _handle_parse_error(self, raw_response: str) -> None:
        """Handle JSON parsing errors."""
        self.logger.error("JSON PARSE ERROR: Invalid JSON format")
        self.memory.add(ActionStep(raw_llm_response=raw_response, error=BAD_JSON))

    def _handle_scratchpad(self, payload: dict[str, Any], raw_response: str) -> None:
        """Handle scratchpad content in payload."""
        self.logger.scratchpad(payload["scratchpad"])
        self.memory.add(
            ScratchpadStep(content=payload["scratchpad"], raw_llm_response=raw_response)
        )
        del payload["scratchpad"]

    def _handle_final_answer(
        self,
        answer: Any,
        start_time: float,
        steps_taken: int,
        return_result: bool,
        finalizer: Finalizer,
        source: Literal["normal", "final_attempt"],
    ) -> str | RunResult:
        """Handle a final answer from the agent."""
        answer_value = str(answer)
        finalizer.set(answer_value, source=source)
        self.logger.final_answer(answer_value)

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

    async def _execute_tool(
        self,
        payload: dict[str, Any],
        raw_response: str,
        temperature: float,
        start_time: float,
        steps_taken: int,
        return_result: bool,
        finalizer: Finalizer,
    ) -> None:
        """Execute a tool call and add result to memory."""
        name = payload.get("tool")
        args = payload.get("arguments", {}) or {}
        if name not in self._tool_map:
            self.logger.error(f"Unknown tool '{name}'")
            self.memory.add(
                ActionStep(
                    tool_name=str(name) if name is not None else "<missing>",
                    tool_args=args,
                    error=f"Unknown tool '{name}'",
                    raw_llm_response=raw_response,
                )
            )
            return

        self.logger.tool_call(name, args)

        ok, result = await self._safe_tool(name, args)
        result_str = str(result)
        short = (result_str[:MAX_OBS_LEN] + "...") if len(result_str) > MAX_OBS_LEN else result_str

        truncated_from = len(result_str) if len(result_str) > MAX_OBS_LEN else None
        self.logger.tool_observation(str(short), is_error=not ok, truncated_from=truncated_from)

        # Add action step to memory
        if ok:
            self.memory.add(
                ActionStep(
                    tool_name=name, tool_args=args, observation=short, raw_llm_response=raw_response
                )
            )
        else:
            self.memory.add(
                ActionStep(
                    tool_name=name, tool_args=args, error=short, raw_llm_response=raw_response
                )
            )

        # Apply pruning if enabled
        if self.enable_pruning:
            self.memory.prune(keep_last_n_steps(self.prune_keep_last))

    async def _attempt_final_answer(
        self,
        start_time: float,
        steps_taken: int,
        return_result: bool,
        finalizer: Finalizer,
    ) -> str | RunResult:
        """Attempt to get a final answer after loop exhaustion."""
        self.logger.final_attempt_header()

        messages = self.memory.to_messages()
        final_try = await self._chat(
            messages + [{"role": "user", "content": "Return your best final answer now."}], 0
        )
        payload = self._try_parse_json(final_try) or {}
        duration = time.time() - start_time

        if "answer" in payload:
            return self._handle_final_answer(
                payload["answer"],
                start_time,
                steps_taken,
                return_result,
                finalizer,
                "final_attempt",
            )

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
            messages=messages,  # type: ignore[arg-type]
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
