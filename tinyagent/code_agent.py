"""
tinyagent.code_agent
Minimal Python-executing ReAct agent with sandboxed code execution.

Public surface
--------------
PythonExecutor  – class
TinyCodeAgent   – class
"""

from __future__ import annotations

import ast
import contextlib
import io
import os
import re
import textwrap
from dataclasses import dataclass
from typing import Any, Final, Sequence

from openai import OpenAI

from .agent import StepLimitReached
from .prompt import CODE_SYSTEM
from .tools import Tool

__all__ = ["PythonExecutor", "TinyCodeAgent"]

# ---------------------------------------------------------------------------
MAX_STEPS: Final = 6
MAX_OUTPUT_LENGTH: Final = 2000


@dataclass
class FinalResult:
    """Sentinel class for final_answer() results."""

    value: Any


class PythonExecutor:
    """Very small, very strict sandbox for Python code execution."""

    SAFE_BUILTINS = {
        "abs",
        "all",
        "any",
        "bool",
        "dict",
        "enumerate",
        "float",
        "int",
        "len",
        "list",
        "max",
        "min",
        "print",
        "range",
        "round",
        "sorted",
        "str",
        "sum",
        "tuple",
        "type",
        "zip",
    }

    def __init__(self, extra_imports: set[str] | None = None):
        """
        Initialize the Python executor with optional extra imports.

        Parameters
        ----------
        extra_imports
            Set of module names allowed to be imported (e.g., {"math", "json"})
        """
        # Build safe globals with restricted builtins
        import builtins

        self._globals = {"__builtins__": {k: getattr(builtins, k) for k in self.SAFE_BUILTINS}}
        # Add __import__ for controlled imports
        self._globals["__builtins__"]["__import__"] = self._safe_import
        # Add final_answer function that returns sentinel
        self._globals["final_answer"] = self._final_answer  # type: ignore[assignment]
        # Track allowed imports
        self._allowed = set(extra_imports or ())

    def run(self, code: str) -> tuple[str, bool]:
        """
        Execute Python code in sandboxed environment.

        Parameters
        ----------
        code
            Python code to execute

        Returns
        -------
        tuple[str, bool]
            (output/result, is_final_answer)
        """
        # Quick import guard using AST
        self._check_imports(code)

        # Capture stdout
        buff = io.StringIO()
        with contextlib.redirect_stdout(buff):
            # Create namespace copy to avoid pollution
            ns = self._globals.copy()

            # Execute code
            exec(code, ns)

            # Check if we have a final answer stored
            if "_final_result" in ns and isinstance(ns["_final_result"], FinalResult):
                return str(ns["_final_result"].value), True

            # Otherwise return stdout
            output = buff.getvalue().strip()
            return output, False

    def _safe_import(self, name, *args, **kwargs):
        """Controlled import function."""
        module_name = name.split(".")[0]
        if module_name not in self._allowed:
            raise RuntimeError(f"Import '{name}' not allowed")
        return __import__(name, *args, **kwargs)

    def _final_answer(self, value):
        """Store final answer in a way that survives exec."""
        # Store in the calling namespace
        import inspect

        frame = inspect.currentframe().f_back
        frame.f_globals["_final_result"] = FinalResult(value)
        return value

    def _check_imports(self, code: str) -> None:
        """Check that all imports are allowed."""
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    if module not in self._allowed:
                        raise RuntimeError(f"Import '{alias.name}' not allowed")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split(".")[0]
                    if module not in self._allowed:
                        raise RuntimeError(f"Import from '{node.module}' not allowed")


@dataclass(kw_only=True)
class TinyCodeAgent:
    """
    A lightweight Python-executing ReAct agent.

    Parameters
    ----------
    tools
        Sequence of Tool objects or @tool decorated functions
    model
        Model name (OpenAI or OpenRouter format). Default "gpt-4o-mini"
        Examples: "gpt-4", "google/gemini-2.0-flash-thinking-exp-1219", "anthropic/claude-3.5-haiku"
    api_key
        Optional OpenAI key; falls back to OPENAI_API_KEY env var
    extra_imports
        Additional modules to allow in Python code (e.g., ["math", "json"])
    system_suffix
        Optional text to append to system prompt (e.g., example calls)
    """

    tools: Sequence[Tool]
    model: str = "gpt-4o-mini"
    api_key: str | None = None
    extra_imports: Sequence[str] = ()
    system_suffix: str = ""

    def __post_init__(self) -> None:
        if not self.tools:
            raise ValueError("TinyCodeAgent requires at least one tool.")

        # Get the registry to look up Tool objects for functions
        from .tools import get_registry

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

        # Initialize Python executor with tools as globals
        self._executor = PythonExecutor(set(self.extra_imports))

        # Add tools to executor globals
        for name, tool in self._tool_map.items():
            self._executor._globals[name] = tool.fn  # type: ignore[assignment]

        # Render immutable system prompt once
        self._system_prompt: str = CODE_SYSTEM.format(helpers=", ".join(self._tool_map.keys()))
        if self.system_suffix:
            self._system_prompt += "\n\n" + self.system_suffix

    def run(self, task: str, *, max_steps: int = MAX_STEPS, verbose: bool = False) -> str:
        """
        Execute the Python-based ReAct loop.

        Parameters
        ----------
        task
            The task/question to solve
        max_steps
            Maximum number of reasoning steps

        verbose
            If True, print detailed logs of execution

        Returns
        -------
        str
            The final answer

        Raises
        ------
        StepLimitReached
            If no answer is found within max_steps
        """
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": task},
        ]

        if verbose:
            print("\n" + "=" * 80)
            print("TINYCODE AGENT STARTING")
            print("=" * 80)
            print(f"\nTASK: {task}")
            print(f"\nSYSTEM PROMPT:\n{self._system_prompt}")
            print(f"\nAVAILABLE TOOLS: {list(self._tool_map.keys())}")
            print(f"\nALLOWED IMPORTS: {list(self._executor._allowed)}")

        for step in range(max_steps):
            if verbose:
                print(f"\n{'=' * 40} STEP {step + 1}/{max_steps} {'=' * 40}")
                print("\nSENDING TO LLM:")
                for msg in messages[-2:]:  # Show last 2 messages
                    print(
                        f"  [{msg['role'].upper()}]: {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}"
                    )
            # Get model response
            reply = self._chat(messages, verbose=verbose)

            # Extract code block
            if verbose:
                print(f"\nLLM RESPONSE:\n{reply}")

            code = self._extract_code(reply)
            if not code:
                if verbose:
                    print("\n[!] No code block found in response")
                # Ask for proper format
                messages += [
                    {"role": "assistant", "content": reply},
                    {"role": "user", "content": "Please respond with a python block only."},
                ]
                continue

            if verbose:
                print(f"\nEXTRACTED CODE:\n{'-' * 40}\n{code}\n{'-' * 40}")

            # Execute code
            try:
                if verbose:
                    print("\nEXECUTING CODE...")
                result, done = self._executor.run(code)
                if verbose:
                    print(f"EXECUTION RESULT: {result}")
                    print(f"IS FINAL ANSWER: {done}")
            except KeyError as e:
                # Special handling for KeyError to help with dict access
                if verbose:
                    print(f"\n[!] KEY ERROR: {e}")
                error_msg = f"KeyError: {e}. "
                # Try to extract available keys from the error context
                if "get_weather" in code:
                    error_msg += "Note: get_weather() returns dict with keys: 'temp', 'condition', 'humidity'"
                elif "fetch_stock_data" in code:
                    error_msg += "Note: fetch_stock_data() returns dict with keys: 'price', 'change', 'volume', 'high', 'low'"
                elif "get_exchange_rate" in code:
                    error_msg += "Note: get_exchange_rate() returns a float value directly"
                # Report error
                messages += [
                    {"role": "assistant", "content": reply},
                    {"role": "user", "content": error_msg},
                ]
                continue
            except Exception as e:
                if verbose:
                    print(f"\n[!] EXECUTION ERROR: {e}")
                # Report error
                messages += [
                    {"role": "assistant", "content": reply},
                    {"role": "user", "content": f"Execution error: {e}"},
                ]
                continue

            # Check if we have final answer
            if done:
                if verbose:
                    print(f"\n{'=' * 80}")
                    print(f"FINAL ANSWER: {result[:MAX_OUTPUT_LENGTH]}")
                    print(f"{'=' * 80}\n")
                return result[:MAX_OUTPUT_LENGTH]  # Truncate if too long

            # Continue with observation
            messages += [
                {"role": "assistant", "content": reply},
                {"role": "user", "content": f"Observation:\n{result}\n"},
            ]

        raise StepLimitReached("Exceeded max ReAct steps without an answer.")

    def _chat(self, messages: list[dict[str, str]], verbose: bool = False) -> str:
        """Single LLM call; OpenAI-compatible."""
        if verbose:
            print(f"\n[API] Calling {self.model}...")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0,
        )
        if verbose:
            print(
                f"[API] Response received (length: {len(response.choices[0].message.content)} chars)"
            )
        return response.choices[0].message.content.strip()

    @staticmethod
    def _extract_code(text: str) -> str | None:
        """Extract Python code block from text."""
        match = re.search(r"```(?:python)?\s*(.+?)```", text, re.DOTALL)
        if match:
            return textwrap.dedent(match.group(1)).strip()
        return None
