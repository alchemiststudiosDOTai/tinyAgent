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

from openai import OpenAI

from ..core.exceptions import StepLimitReached
from ..core.finalizer import Finalizer
from ..core.registry import Tool, get_registry
from ..core.types import RunResult
from ..prompts.loader import get_prompt_fallback
from ..prompts.templates import BAD_JSON, SYSTEM

__all__ = ["ReactAgent"]

# ---------------------------------------------------------------------------
MAX_STEPS: Final = 10
TEMP_STEP: Final = 0.2
MAX_OBS_LEN: Final = 500  # added this to not bnlow up the prompt


@dataclass(kw_only=True)
class ReactAgent:
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

        # Get the base system prompt (from file or default)
        base_prompt = get_prompt_fallback(SYSTEM, self.prompt_file)

        # Render immutable system prompt once
        self._system_prompt: str = base_prompt.format(
            tools="\n".join(
                f"- {t.name}: {t.doc or '<no description>'} | args={t.signature}"
                for t in self._tool_map.values()
            )
        )

    # ------------------------------------------------------------------
    def run(
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
        # Initialize execution tracking
        start_time = time.time()
        finalizer = Finalizer()
        steps_taken = 0

        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": question},
        ]
        temperature = self.temperature

        if verbose:
            print("\n" + "=" * 80)
            print("REACT AGENT STARTING")
            print("=" * 80)
            print(f"\nTASK: {question}")
            print(f"\nSYSTEM PROMPT:\n{self._system_prompt}")
            print(f"\nAVAILABLE TOOLS: {list(self._tool_map.keys())}")

        for step in range(max_steps):
            steps_taken = step + 1
            if verbose:
                print(f"\n{'=' * 40} STEP {steps_taken}/{max_steps} {'=' * 40}")
                print("\nSENDING TO LLM:")
                for msg in messages[-2:]:
                    content_preview = (
                        msg["content"][:200] + "..."
                        if len(msg["content"]) > 200
                        else msg["content"]
                    )
                    print(f"  [{msg['role'].upper()}]: {content_preview}")

            assistant_reply = self._chat(messages, temperature, verbose=verbose)

            if verbose:
                print(f"\nLLM RESPONSE:\n{assistant_reply}")

            payload = self._try_parse_json(assistant_reply)

            # If JSON malformed → ask model to fix
            if payload is None:
                if verbose:
                    print("\n[!] JSON PARSE ERROR: Invalid JSON format")
                messages += [
                    {"role": "assistant", "content": assistant_reply},
                    {"role": "user", "content": BAD_JSON},
                ]
                temperature += TEMP_STEP
                continue

            # Handle scratchpad - log it, then remove from payload
            # The scratchpad field allows the model to plan/think before taking action
            if "scratchpad" in payload:
                if verbose:
                    print(f"\n[SCRATCHPAD]: {payload['scratchpad']}")
                messages += [
                    {"role": "assistant", "content": assistant_reply},
                    {"role": "user", "content": f"Scratchpad noted: {payload['scratchpad']}"},
                ]
                del payload["scratchpad"]
                # Ask the model to resend proper JSON if nothing actionable left
                if "answer" not in payload and "tool" not in payload:
                    temperature += TEMP_STEP
                    continue

            # Final answer path
            if "answer" in payload:
                answer_value = str(payload["answer"])
                finalizer.set(answer_value, source="normal")

                if verbose:
                    print(f"\n{'=' * 80}")
                    print(f"FINAL ANSWER: {answer_value}")
                    print(f"{'=' * 80}\n")

                # Return based on requested format
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

            # Tool invocation path
            name = payload.get("tool")
            args = payload.get("arguments", {}) or {}
            if name not in self._tool_map:
                return f"Unknown tool '{name}'."

            if verbose:
                print(f"\n[TOOL CALL]: {name}")
                print(f"[ARGUMENTS]: {args}")

            ok, result = self._safe_tool(name, args, verbose=verbose)
            tag = "Observation" if ok else "Error"
            short = (str(result)[:MAX_OBS_LEN] + "…") if len(str(result)) > MAX_OBS_LEN else result

            if verbose:
                print(f"[{tag.upper()}]: {short}")
                if len(str(result)) > MAX_OBS_LEN:
                    print(
                        f"[NOTE]: Output truncated from {len(str(result))} to {MAX_OBS_LEN} chars"
                    )

            messages += [
                {"role": "assistant", "content": assistant_reply},
                {"role": "user", "content": f"{tag}: {short}"},
            ]

        # Step limit hit → ask once for best guess
        if verbose:
            print(f"\n{'=' * 40} FINAL ATTEMPT {'=' * 40}")
            print("[!] Step limit reached. Asking for final answer...")

        final_try = self._chat(
            messages + [{"role": "user", "content": "Return your best final answer now."}],
            0,
            verbose=verbose,
        )
        payload = self._try_parse_json(final_try) or {}
        duration = time.time() - start_time

        if "answer" in payload:
            answer_value = str(payload["answer"])
            finalizer.set(answer_value, source="final_attempt")

            if verbose:
                print(f"\n{'=' * 80}")
                print(f"FINAL ANSWER: {answer_value}")
                print(f"{'=' * 80}\n")

            # Return based on requested format
            if return_result:
                return RunResult(
                    output=answer_value,
                    final_answer=finalizer.get(),
                    state="step_limit_reached",
                    steps_taken=steps_taken,
                    duration_seconds=duration,
                )
            return answer_value

        # No final answer obtained
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
    def _chat(
        self, messages: list[dict[str, str]], temperature: float, verbose: bool = False
    ) -> str:
        """Single LLM call; OpenAI-compatible."""
        if verbose:
            print(f"\n[API] Calling {self.model} (temp={temperature})...")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        if verbose:
            print(
                f"[API] Response received (length: {len(response.choices[0].message.content)} chars)"
            )
        return response.choices[0].message.content.strip()

    @staticmethod
    def _try_parse_json(text: str) -> dict[str, Any] | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def _safe_tool(
        self, name: str, args: dict[str, Any], verbose: bool = False
    ) -> tuple[bool, Any]:
        """
        Execute tool with argument validation.

        Returns (success: bool, result: Any)
        """
        tool = self._tool_map[name]

        # Basic arg validation using function signature
        from inspect import signature

        try:
            signature(tool.fn).bind(**args)
        except TypeError as exc:
            if verbose:
                print(f"[!] ARGUMENT ERROR: {exc}")
            return False, f"ArgError: {exc}"

        try:
            if verbose:
                print(f"[EXECUTING]: {name}({args})")
            result = tool.run(args)
            if verbose:
                print(f"[RESULT]: {result}")
            return True, result
        except Exception as exc:  # pragma: no cover
            if verbose:
                print(f"[!] TOOL ERROR: {exc}")
            return False, f"ToolError: {exc}"
