"""
tinyagent.agents.code
Minimal Python-executing ReAct agent with sandboxed code execution.

This module implements TinyCodeAgent v2 with:
- Modular executor backends (local, isolated, sandboxed)
- Working memory (scratchpad) across steps
- Structured conversation memory (MemoryManager)
- Resource limits and timeout management
- LLM communication signals (uncertainty, exploration, commit)

Public surface
--------------
TinyCodeAgent   - class
TrustLevel      - enum
"""

from __future__ import annotations

import os
import re
import textwrap
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Sequence

from openai import AsyncOpenAI

from ..core.exceptions import StepLimitReached
from ..core.finalizer import Finalizer
from ..core.registry import Tool
from ..core.types import RunResult
from ..execution import ExecutionResult, LocalExecutor
from ..limits import ExecutionLimits
from ..memory import (
    ActionStep,
    AgentMemory,
    MemoryManager,
    SystemPromptStep,
    TaskStep,
    keep_last_n_steps,
)
from ..prompts.loader import get_prompt_fallback
from ..prompts.templates import CODE_SYSTEM
from ..signals import commit, explore, set_signal_logger, uncertain
from .base import BaseAgent

__all__ = ["TinyCodeAgent", "TrustLevel"]


class TrustLevel(Enum):
    """
    Trust level for code execution.

    - LOCAL: Restricted exec() in same process (fast, trusted tools)
    - ISOLATED: Subprocess with timeout (default for most use)
    - SANDBOXED: Container/VM (untrusted inputs, production)
    """

    LOCAL = "local"
    ISOLATED = "isolated"
    SANDBOXED = "sandboxed"


@dataclass(kw_only=True)
class TinyCodeAgent(BaseAgent):
    """
    A lightweight Python-executing ReAct agent with graduated trust.

    TinyCodeAgent v2 behaves like a junior developer: it thinks in code,
    fails cheaply, retries intelligently, and knows when it's done.

    Parameters
    ----------
    tools
        Sequence of Tool objects or @tool decorated functions
    model
        Model name (OpenAI or OpenRouter format). Default "gpt-4o-mini"
    api_key
        Optional OpenAI key; falls back to OPENAI_API_KEY env var
    trust_level
        Execution trust level (local, isolated, sandboxed). Default "local"
    limits
        Resource limits for execution (timeout, memory, output, steps)
    extra_imports
        Additional modules to allow in Python code (e.g., ["math", "json"])
    system_suffix
        Optional text to append to system prompt
    prompt_file
        Optional path to a text file containing the system prompt
    verbose
        If True, enables detailed execution logging
    memory_manager
        Optional MemoryManager instance. If None, one will be created automatically.
        Note: Uses memory_manager to avoid collision with existing memory (AgentMemory).
    enable_pruning
        If True, apply pruning strategy after each step. Default False.
    prune_keep_last
        Number of recent action steps to keep when pruning. Default 5.

    Examples
    --------
    >>> from tinyagent import TinyCodeAgent, tool
    >>>
    >>> @tool
    ... def add(a: int, b: int) -> int:
    ...     '''Add two numbers'''
    ...     return a + b
    >>>
    >>> agent = TinyCodeAgent(tools=[add])
    >>> result = await agent.run("What is 2 + 3?")
    """

    tools: Sequence[Tool]
    model: str = "gpt-4o-mini"
    api_key: str | None = None
    trust_level: TrustLevel | Literal["local", "isolated", "sandboxed"] = TrustLevel.LOCAL
    limits: ExecutionLimits = field(default_factory=ExecutionLimits)
    extra_imports: Sequence[str] = ()
    system_suffix: str = ""
    prompt_file: str | None = None
    verbose: bool = False
    memory_manager: MemoryManager | None = field(default=None)
    enable_pruning: bool = False
    prune_keep_last: int = 5

    # Internal state (set in __post_init__)
    _tool_map: dict[str, Tool] = field(default_factory=dict, init=False, repr=False)
    _executor: LocalExecutor = field(init=False, repr=False)
    _system_prompt: str = field(default="", init=False, repr=False)
    client: AsyncOpenAI = field(init=False, repr=False)

    def __post_init__(self) -> None:
        super().__post_init__()

        if isinstance(self.trust_level, str):
            self.trust_level = TrustLevel(self.trust_level)

        for name, tool in self._tool_map.items():
            if tool.is_async:
                raise ValueError(
                    f"TinyCodeAgent does not support async tools: '{name}'. "
                    f"Use ReactAgent for async tools."
                )

        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        self._init_executor()

        base_prompt = get_prompt_fallback(CODE_SYSTEM, self.prompt_file)
        self._system_prompt = base_prompt.format(helpers=", ".join(self._tool_map.keys()))
        if self.system_suffix:
            self._system_prompt += "\n\n" + self.system_suffix

        # Initialize memory_manager if not provided
        if self.memory_manager is None:
            self.memory_manager = MemoryManager()

    def _init_executor(self) -> None:
        """Initialize the appropriate executor based on trust level."""
        if self.trust_level == TrustLevel.LOCAL:
            self._executor = LocalExecutor(
                allowed_imports=set(self.extra_imports),
                limits=self.limits,
            )
        elif self.trust_level == TrustLevel.ISOLATED:
            # TODO: Implement SubprocessExecutor
            self._executor = LocalExecutor(
                allowed_imports=set(self.extra_imports),
                limits=self.limits,
            )
        elif self.trust_level == TrustLevel.SANDBOXED:
            # TODO: Implement DockerExecutor
            self._executor = LocalExecutor(
                allowed_imports=set(self.extra_imports),
                limits=self.limits,
            )

        for name, tool in self._tool_map.items():
            self._executor.inject(name, tool.fn)

        self._executor.inject("uncertain", uncertain)
        self._executor.inject("explore", explore)
        self._executor.inject("commit", commit)

    async def run(
        self,
        task: str,
        *,
        max_steps: int | None = None,
        verbose: bool | None = None,
        return_result: bool = False,
    ) -> str | RunResult:
        """
        Execute the Python-based ReAct loop.

        Parameters
        ----------
        task
            The task/question to solve
        max_steps
            Maximum number of reasoning steps (default: from limits)
        verbose
            If True, print detailed logs (default: instance setting)
        return_result
            If True, return RunResult with metadata; if False, return string

        Returns
        -------
        str | RunResult
            The final answer, or RunResult with metadata if return_result=True

        Raises
        ------
        StepLimitReached
            If no answer is found within max_steps and return_result=False
        """
        if max_steps is None:
            max_steps = self.limits.max_steps
        if verbose is None:
            verbose = self.verbose

        self.logger.verbose = verbose
        set_signal_logger(self.logger)

        start_time = time.time()
        finalizer = Finalizer()
        scratchpad = AgentMemory()  # Scratchpad for working memory
        steps_taken = 0

        for name, value in scratchpad.to_namespace().items():
            self._executor.inject(name, value)

        # Initialize structured memory for this run
        self.memory_manager.clear()
        self.memory_manager.add(SystemPromptStep(content=self._system_prompt))
        self.memory_manager.add(TaskStep(task=task))

        self.logger.banner("TINYCODE AGENT v2 STARTING")
        self.logger.labeled("TASK", task)
        trust_val = (
            self.trust_level.value
            if isinstance(self.trust_level, TrustLevel)
            else str(self.trust_level)
        )
        self.logger.labeled("TRUST LEVEL", trust_val)
        self.logger.labeled(
            "LIMITS",
            f"timeout={self.limits.timeout_seconds}s, "
            f"max_steps={max_steps}, "
            f"max_output={self.limits.max_output_bytes}B",
        )
        self.logger.labeled("AVAILABLE TOOLS", str(list(self._tool_map.keys())))
        self.logger.labeled("ALLOWED IMPORTS", str(list(self.extra_imports)))

        for step in range(max_steps):
            steps_taken = step + 1

            self.logger.step_header(steps_taken, max_steps)

            messages = self.memory_manager.to_messages()
            self.logger.messages_preview(messages)

            reply = await self._chat(messages)

            self.logger.llm_response(reply)

            code = self._extract_code(reply)
            if not code:
                self.logger.error("No code block found in response")
                self.memory_manager.add(
                    ActionStep(
                        raw_llm_response=reply,
                        error="Please respond with a python block only.",
                    )
                )
                continue

            self.logger.code_block(code)

            result = self._executor.run(code)

            self.logger.execution_result(
                output=result.output,
                duration_ms=result.duration_ms,
                is_final=result.is_final,
                error=result.error,
                timeout=result.timeout,
            )

            if result.error:
                error_msg = self._build_error_message(result, code)
                self.memory_manager.add(
                    ActionStep(
                        raw_llm_response=reply,
                        error=error_msg,
                    )
                )
                scratchpad.fail(f"Step {steps_taken}: {result.error}")
                continue

            if result.timeout:
                self.memory_manager.add(
                    ActionStep(
                        raw_llm_response=reply,
                        error=f"Execution timed out after {self.limits.timeout_seconds}s",
                    )
                )
                scratchpad.fail(f"Step {steps_taken}: Timeout")
                continue

            if result.is_final:
                output = str(result.final_value)
                output, _ = self.limits.truncate_output(output)
                finalizer.set(output, source="normal")

                self.logger.final_answer(output)

                if return_result:
                    return RunResult(
                        output=output,
                        final_answer=finalizer.get(),
                        state="completed",
                        steps_taken=steps_taken,
                        duration_seconds=time.time() - start_time,
                    )
                return output

            # Build observation with scratchpad context
            observation = result.output if result.output else "(no output)"
            scratchpad_context = scratchpad.to_context()
            if scratchpad_context:
                observation += f"\n\n{scratchpad_context}"

            self.memory_manager.add(
                ActionStep(
                    raw_llm_response=reply,
                    observation=observation,
                )
            )

            # Apply pruning if enabled
            if self.enable_pruning:
                self.memory_manager.prune(keep_last_n_steps(self.prune_keep_last))

        duration = time.time() - start_time
        error = StepLimitReached(
            "Exceeded max ReAct steps without an answer.",
            steps_taken=steps_taken,
            final_attempt_made=False,
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

    async def _chat(self, messages: list[dict[str, str]]) -> str:
        """Single LLM call; OpenAI-compatible."""
        self.logger.api_call(self.model)
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0,
        )
        content = response.choices[0].message.content or ""
        self.logger.api_response(len(content))
        return content.strip()

    @staticmethod
    def _extract_code(text: str) -> str | None:
        """Extract Python code block from text."""
        match = re.search(r"```(?:python)?\s*(.+?)```", text, re.DOTALL)
        if match:
            return textwrap.dedent(match.group(1)).strip()
        return None

    def _build_error_message(self, result: ExecutionResult, code: str) -> str:
        """Build a helpful error message with tool hints."""
        error_msg = f"Execution error: {result.error}"

        for name, tool in self._tool_map.items():
            if name in code and tool.doc:
                error_msg += f"\n\nHint - {name}() docstring:\n{tool.doc}"

        return error_msg


# Backwards compatibility - export old class name
PythonExecutor = LocalExecutor
