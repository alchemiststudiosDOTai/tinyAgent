"""
tinyagent.limits.boundaries
Resource limits and timeout wrapper for code execution.

Public surface
--------------
ExecutionLimits  – dataclass
ExecutionTimeout – exception
"""

from __future__ import annotations

import signal
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

__all__ = ["ExecutionLimits", "ExecutionTimeout"]


class ExecutionTimeout(TimeoutError):
    """Raised when code execution exceeds the time limit."""

    def __init__(self, message: str = "Execution timed out", *, timeout_seconds: float):
        super().__init__(message)
        self.timeout_seconds = timeout_seconds


@dataclass(frozen=True)
class ExecutionLimits:
    """
    Resource limits for code execution.

    Parameters
    ----------
    timeout_seconds : float
        Maximum execution time in seconds (default: 30)
    max_memory_mb : int
        Maximum memory usage in MB (default: 256, tracking only)
    max_output_bytes : int
        Maximum output size in bytes (default: 10000)
    max_steps : int
        Maximum number of agent steps (default: 10)
    """

    timeout_seconds: float = 30.0
    max_memory_mb: int = 256
    max_output_bytes: int = 10_000
    max_steps: int = 10

    @contextmanager
    def timeout_context(self) -> Iterator[None]:
        """
        Context manager that raises ExecutionTimeout after timeout_seconds.

        Uses threading.Timer for cross-platform compatibility.
        On Unix systems with signal support, prefers signal-based timeout.

        Yields
        ------
        None

        Raises
        ------
        ExecutionTimeout
            If execution exceeds timeout_seconds
        """
        if self.timeout_seconds <= 0:
            yield
            return

        # Try signal-based timeout on Unix (more reliable for CPU-bound code)
        if hasattr(signal, "SIGALRM") and threading.current_thread() is threading.main_thread():
            yield from self._signal_timeout()
        else:
            yield from self._timer_timeout()

    def _signal_timeout(self) -> Iterator[None]:
        """Signal-based timeout (Unix only, main thread only)."""

        def handler(signum: int, frame: object) -> None:
            raise ExecutionTimeout(
                f"Execution timed out after {self.timeout_seconds}s",
                timeout_seconds=self.timeout_seconds,
            )

        old_handler = signal.signal(signal.SIGALRM, handler)
        signal.setitimer(signal.ITIMER_REAL, self.timeout_seconds)
        try:
            yield
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)

    def _timer_timeout(self) -> Iterator[None]:
        """Threading-based timeout (cross-platform, less reliable for CPU-bound)."""
        timed_out = threading.Event()

        def timeout_handler() -> None:
            timed_out.set()

        timer = threading.Timer(self.timeout_seconds, timeout_handler)
        timer.start()
        try:
            yield
            if timed_out.is_set():
                raise ExecutionTimeout(
                    f"Execution timed out after {self.timeout_seconds}s",
                    timeout_seconds=self.timeout_seconds,
                )
        finally:
            timer.cancel()

    def truncate_output(self, output: str) -> tuple[str, bool]:
        """
        Truncate output to max_output_bytes.

        Parameters
        ----------
        output : str
            Output string to potentially truncate

        Returns
        -------
        tuple[str, bool]
            (truncated_output, was_truncated)
        """
        output_bytes = output.encode("utf-8")
        if len(output_bytes) <= self.max_output_bytes:
            return output, False

        truncated = output_bytes[: self.max_output_bytes].decode("utf-8", errors="ignore")
        return truncated + "\n[OUTPUT TRUNCATED]", True
