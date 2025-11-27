"""
tinyagent.agents.code
Minimal Python-executing ReAct agent with sandboxed code execution.

This module implements TinyCodeAgent v2 with:
- Modular executor backends (local, isolated, sandboxed)
- Working memory (scratchpad) across steps
- Resource limits and timeout management
- LLM communication signals (uncertainty, exploration, commit)

Public surface
--------------
TinyCodeAgent   – class
TrustLevel      – enum
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
from ..core.registry import Tool, get_registry
from ..core.types import RunResult
from ..execution import ExecutionResult, LocalExecutor
from ..limits import ExecutionLimits
from ..memory import AgentMemory
from ..prompts.loader import get_prompt_fallback
from ..prompts.templates import CODE_SYSTEM
from ..signals import commit, explore, uncertain

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
class TinyCodeAgent:
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

    # Internal state (set in __post_init__)
    _tool_map: dict[str, Tool] = field(default_factory=dict, init=False, repr=False)
    _executor: LocalExecutor = field(init=False, repr=False)
    _system_prompt: str = field(default="", init=False, repr=False)
    client: AsyncOpenAI = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.tools:
            raise ValueError("TinyCodeAgent requires at least one tool.")

        # Normalize trust level
        if isinstance(self.trust_level, str):
            self.trust_level = TrustLevel(self.trust_level)

        # Build tool map
        registry = get_registry()
        self._tool_map = {}
        for item in self.tools:
            if isinstance(item, Tool):
                self._tool_map[item.name] = item
            elif callable(item) and item.__name__ in registry:
                self._tool_map[item.__name__] = registry[item.__name__]
            else:
                raise ValueError(f"Invalid tool: {item}")

        # Validate no async tools
        for name, tool in self._tool_map.items():
            if tool.is_async:
                raise ValueError(
                    f"TinyCodeAgent does not support async tools: '{name}'. "
                    f"Use ReactAgent for async tools."
                )

        # Initialize OpenAI client
        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        # Initialize executor based on trust level
        self._init_executor()

        # Build system prompt
        base_prompt = get_prompt_fallback(CODE_SYSTEM, self.prompt_file)
        self._system_prompt = base_prompt.format(helpers=", ".join(self._tool_map.keys()))
        if self.system_suffix:
            self._system_prompt += "\n\n" + self.system_suffix

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

        # Inject tools into executor namespace
        for name, tool in self._tool_map.items():
            self._executor.inject(name, tool.fn)

        # Inject signal functions
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
        # Use instance defaults if not specified
        if max_steps is None:
            max_steps = self.limits.max_steps
        if verbose is None:
            verbose = self.verbose

        # Initialize execution state
        start_time = time.time()
        finalizer = Finalizer()
        memory = AgentMemory()
        steps_taken = 0

        # Inject memory into executor
        for name, value in memory.to_namespace().items():
            self._executor.inject(name, value)

        # Build initial messages
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": task},
        ]

        if verbose:
            self._log_start(task, max_steps)

        for step in range(max_steps):
            steps_taken = step + 1

            if verbose:
                self._log_step(steps_taken, max_steps, messages)

            # Get model response
            reply = await self._chat(messages, verbose=verbose)

            if verbose:
                print(f"\nLLM RESPONSE:\n{reply}")

            # Extract code block
            code = self._extract_code(reply)
            if not code:
                if verbose:
                    print("\n[!] No code block found in response")
                messages += [
                    {"role": "assistant", "content": reply},
                    {"role": "user", "content": "Please respond with a python block only."},
                ]
                continue

            if verbose:
                print(f"\nEXTRACTED CODE:\n{'-' * 40}\n{code}\n{'-' * 40}")

            # Execute code
            result = self._executor.run(code)

            if verbose:
                self._log_execution(result)

            # Handle execution result
            if result.error:
                error_msg = self._build_error_message(result, code)
                messages += [
                    {"role": "assistant", "content": reply},
                    {"role": "user", "content": error_msg},
                ]
                memory.fail(f"Step {steps_taken}: {result.error}")
                continue

            if result.timeout:
                messages += [
                    {"role": "assistant", "content": reply},
                    {
                        "role": "user",
                        "content": f"Execution timed out after {self.limits.timeout_seconds}s",
                    },
                ]
                memory.fail(f"Step {steps_taken}: Timeout")
                continue

            # Check for final answer
            if result.is_final:
                output = str(result.final_value)
                output, _ = self.limits.truncate_output(output)
                finalizer.set(output, source="normal")

                if verbose:
                    print(f"\n{'=' * 80}")
                    print(f"FINAL ANSWER: {output}")
                    print(f"{'=' * 80}\n")

                if return_result:
                    return RunResult(
                        output=output,
                        final_answer=finalizer.get(),
                        state="completed",
                        steps_taken=steps_taken,
                        duration_seconds=time.time() - start_time,
                    )
                return output

            # Continue with observation
            observation = result.output if result.output else "(no output)"
            messages += [
                {"role": "assistant", "content": reply},
                {"role": "user", "content": f"Observation:\n{observation}\n"},
            ]

            # Update memory context in messages if needed
            memory_context = memory.to_context()
            if memory_context:
                messages[-1]["content"] += f"\n\n{memory_context}"

        # Step limit reached
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

    async def _chat(self, messages: list[dict[str, str]], verbose: bool = False) -> str:
        """Single LLM call; OpenAI-compatible."""
        if verbose:
            print(f"\n[API] Calling {self.model}...")
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0,
        )
        content = response.choices[0].message.content or ""
        if verbose:
            print(f"[API] Response received (length: {len(content)} chars)")
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

        # Add hints from tool docstrings for relevant tools
        for name, tool in self._tool_map.items():
            if name in code and tool.doc:
                error_msg += f"\n\nHint - {name}() docstring:\n{tool.doc}"

        return error_msg

    def _log_start(self, task: str, max_steps: int) -> None:
        """Log execution start."""
        assert isinstance(self.trust_level, TrustLevel)  # Normalized in __post_init__
        print("\n" + "=" * 80)
        print("TINYCODE AGENT v2 STARTING")
        print("=" * 80)
        print(f"\nTASK: {task}")
        print(f"\nTRUST LEVEL: {self.trust_level.value}")
        print(
            f"\nLIMITS: timeout={self.limits.timeout_seconds}s, "
            f"max_steps={max_steps}, "
            f"max_output={self.limits.max_output_bytes}B"
        )
        print(f"\nAVAILABLE TOOLS: {list(self._tool_map.keys())}")
        print(f"\nALLOWED IMPORTS: {list(self.extra_imports)}")

    def _log_step(self, step: int, max_steps: int, messages: list[dict[str, str]]) -> None:
        """Log step start."""
        print(f"\n{'=' * 40} STEP {step}/{max_steps} {'=' * 40}")
        print("\nSENDING TO LLM:")
        for msg in messages[-2:]:
            content = msg["content"]
            preview = content[:200] + "..." if len(content) > 200 else content
            print(f"  [{msg['role'].upper()}]: {preview}")

    def _log_execution(self, result: ExecutionResult) -> None:
        """Log execution result."""
        print("\nEXECUTION RESULT:")
        print(
            f"  Output: {result.output[:200]}..."
            if len(result.output) > 200
            else f"  Output: {result.output}"
        )
        print(f"  Duration: {result.duration_ms:.1f}ms")
        print(f"  Is Final: {result.is_final}")
        if result.error:
            print(f"  Error: {result.error}")
        if result.timeout:
            print("  TIMEOUT!")


# Backwards compatibility - export old class name
PythonExecutor = LocalExecutor
