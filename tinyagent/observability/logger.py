"""
tinyagent.observability.logger
Centralized logging for agent execution.

This module provides a structured logger that replaces scattered print statements
with a testable, configurable output system.

Public surface
--------------
AgentLogger - class
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any, TextIO

__all__ = ["AgentLogger"]


@dataclass
class AgentLogger:
    """
    Centralized logging for agent execution.

    Provides formatted output for agent operations including banners,
    tagged messages, step progress, and final answers. All output methods
    respect the verbose flag except where noted.

    Parameters
    ----------
    verbose : bool
        If True, output is written. If False, output is suppressed.
    stream : TextIO
        Output stream (default: sys.stdout). Use io.StringIO for testing.
    banner_width : int
        Width of full-width banners (default: 80)
    half_banner_width : int
        Width of half-width banners for step headers (default: 40)
    content_preview_len : int
        Default truncation length for content previews (default: 200)
    observation_max_len : int
        Maximum length for observations (default: 500)
    channel_label_width : int
        Width used for channel prefixes (default: 12)
    """

    verbose: bool = False
    stream: TextIO = field(default_factory=lambda: sys.stdout)
    banner_width: int = 80
    half_banner_width: int = 40
    content_preview_len: int = 200
    observation_max_len: int = 500
    channel_label_width: int = 12

    # --- Banner and section methods ---

    def banner(self, title: str, width: int | None = None) -> None:
        """Print a section banner with dividers."""
        if not self.verbose:
            return
        w = width or self.banner_width
        self._panel(f"COMMAND CENTER // {title}", width=w)

    def step_header(self, step: int, max_steps: int) -> None:
        """Print step progress header."""
        if not self.verbose:
            return
        width = self.half_banner_width * 2
        self._panel(f"OPERATION {step}/{max_steps}", lines=["STATUS :: ADVANCING"], width=width)

    def final_attempt_header(self) -> None:
        """Print final attempt header when step limit reached."""
        if not self.verbose:
            return
        self._panel(
            "FINAL ATTEMPT",
            lines=["[!] Step limit reached. Asking for final answer..."],
            width=self.banner_width,
        )

    def final_answer(self, answer: str) -> None:
        """Print final answer with prominent formatting."""
        if not self.verbose:
            return
        self._panel("FINAL ANSWER", lines=[f"PAYLOAD :: {answer}"], width=self.banner_width)

    # --- Labeled output methods ---

    def labeled(self, label: str, value: str) -> None:
        """Print a labeled value (e.g., TASK: value)."""
        if not self.verbose:
            return
        self._channel(label, value)

    def tag(self, tag: str, message: str, truncate: int | None = None) -> None:
        """Print a tagged message like [API]: content."""
        if not self.verbose:
            return
        content = self.truncate(message, truncate) if truncate else message
        self._channel(tag.upper(), content)

    def error(self, message: str) -> None:
        """Print error message with [!] prefix."""
        if not self.verbose:
            return
        self._channel("ALERT", f"[!] {message}")

    def scratchpad(self, content: str) -> None:
        """Print scratchpad content."""
        if not self.verbose:
            return
        self._panel("SCRATCHPAD", lines=[content], width=self.banner_width)

    # --- LLM communication methods ---

    def messages_preview(self, messages: list[dict[str, str]], last_n: int = 2) -> None:
        """Print preview of recent messages being sent to LLM."""
        if not self.verbose:
            return
        lines = []
        for msg in messages[-last_n:]:
            role = msg["role"].upper()
            content = self.truncate(msg["content"], self.content_preview_len)
            lines.append(f"{role:>9} :: {content}")
        self._panel("LLM TRAFFIC // OUTBOUND", lines=lines, width=self.banner_width)

    def llm_response(self, response: str) -> None:
        """Print LLM response."""
        if not self.verbose:
            return
        payload = self.truncate(response, self.content_preview_len)
        self._panel("LLM RESPONSE", lines=[payload], width=self.banner_width)

    def api_call(self, model: str, temperature: float | None = None) -> None:
        """Log API call being made."""
        if not self.verbose:
            return
        base = f"Calling {model}"
        message = f"{base} (temp={temperature})" if temperature is not None else base
        self._channel("API", f"{message}...")

    def api_response(self, length: int) -> None:
        """Log API response received."""
        if not self.verbose:
            return
        self._channel("API", f"Response received (length: {length} chars)")

    # --- Tool execution methods ---

    def tool_call(self, name: str, args: dict[str, Any]) -> None:
        """Log tool call."""
        if not self.verbose:
            return
        self._panel(f"TOOL CALL // {name}", lines=[f"ARGS :: {args}"], width=self.banner_width)

    def tool_executing(self, name: str, args: dict[str, Any]) -> None:
        """Log tool execution start."""
        if not self.verbose:
            return
        self._channel("EXEC", f"{name}({args})")

    def tool_result(self, result: str, tag: str = "RESULT") -> None:
        """Log tool result."""
        if not self.verbose:
            return
        self._channel(tag.upper(), result)

    def tool_observation(
        self, result: str, is_error: bool = False, truncated_from: int | None = None
    ) -> None:
        """Log tool observation with optional truncation notice."""
        if not self.verbose:
            return
        tag = "ERROR" if is_error else "OBSERVATION"
        self._channel(tag, result)
        if truncated_from is not None:
            notice = f"Output truncated from {truncated_from} to {self.observation_max_len} chars"
            self._channel("NOTE", notice)

    def tool_error(self, error_type: str, message: str) -> None:
        """Log tool error with type prefix."""
        if not self.verbose:
            return
        self._channel("ERROR", f"{error_type}: {message}")

    # --- Code execution methods (TinyCodeAgent) ---

    def code_block(self, code: str) -> None:
        """Print extracted code block."""
        if not self.verbose:
            return
        code_lines = [line for line in code.splitlines()] or ["<empty>"]
        numbered = [f"{idx + 1:>3}: {line}" for idx, line in enumerate(code_lines)]
        self._panel("EXTRACTED CODE", lines=numbered, width=self.banner_width)

    def execution_result(
        self,
        output: str,
        duration_ms: float,
        is_final: bool,
        error: str | None = None,
        timeout: bool = False,
    ) -> None:
        """Log code execution result (for TinyCodeAgent)."""
        if not self.verbose:
            return
        display_output = self.truncate(output, self.content_preview_len)
        lines = [
            f"OUTPUT   :: {display_output}",
            f"DURATION :: {duration_ms:.1f}ms",
            f"FINAL    :: {is_final}",
        ]
        if error:
            lines.append(f"ERROR    :: {error}")
        if timeout:
            lines.append("TIMEOUT  :: TRUE")
        self._panel("EXECUTION RESULT", lines=lines, width=self.banner_width)

    # --- Signal methods ---

    def signal(self, signal_type: str, message: str) -> None:
        """Print a signal (respects verbose flag)."""
        if not self.verbose:
            return
        self._channel(signal_type, message)

    # --- Raw output ---

    def _write(self, text: str) -> None:
        """Write text without newline."""
        self.stream.write(text)
        self.stream.flush()

    def _writeln(self, text: str = "") -> None:
        """Write text with newline."""
        self.stream.write(text + "\n")
        self.stream.flush()

    # --- Utilities ---

    def _panel(self, title: str, lines: list[str] | None = None, width: int | None = None) -> None:
        """Render a framed panel for Command Center style output."""
        w = width or self.banner_width
        border = f"+{'=' * (w - 2)}+"
        divider = f"+{'-' * (w - 2)}+"

        self._writeln()
        self._writeln(border)
        self._writeln(self._panel_title(title, w))

        if lines:
            self._writeln(divider)
            for line in lines:
                for chunk in self._multiline(line):
                    self._writeln(f"| {self._pad(chunk, w - 4)} |")
            self._writeln(border)
        else:
            self._writeln(border)

    def _panel_title(self, title: str, width: int) -> str:
        """Format a panel title centered within the frame."""
        label = f"<< {title} >>"
        return f"| {self._pad(label, width - 4)} |"

    def _channel(self, tag: str, message: str) -> None:
        """Render a single-line HUD channel."""
        prefix = self._channel_prefix(tag)
        for line in self._multiline(message):
            self._writeln(f"{prefix} >> {line}")

    def _channel_prefix(self, tag: str) -> str:
        """Format channel prefix with consistent width."""
        label = tag.upper()
        padded = f"{label:^{self.channel_label_width}}"
        return f"[{padded}]"

    def _multiline(self, text: str) -> list[str]:
        """Split text into lines, preserving empty content."""
        lines = text.splitlines()
        return lines or [""]

    def _pad(self, text: str, width: int) -> str:
        """Truncate and pad text to fit panel width."""
        trimmed = self.truncate(text, width)
        return trimmed.ljust(width)

    def truncate(self, text: str, max_len: int | None = None) -> str:
        """Truncate text with ellipsis indicator."""
        limit = max_len or self.content_preview_len
        if len(text) <= limit:
            return text
        return text[:limit] + "..."

    def captured(self) -> str:
        """Get captured output (for testing with StringIO)."""
        if hasattr(self.stream, "getvalue"):
            return self.stream.getvalue()
        return ""
