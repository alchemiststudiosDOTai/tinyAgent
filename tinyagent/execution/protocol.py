"""
tinyagent.execution.protocol
Executor protocol defining the interface for code execution backends.

Public surface
--------------
Executor         – Protocol
ExecutionResult  – dataclass
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

__all__ = ["Executor", "ExecutionResult"]


@dataclass(frozen=True)
class ExecutionResult:
    """
    Result of a code execution with metadata.

    Parameters
    ----------
    output : str
        The captured output (stdout) from execution
    is_final : bool
        Whether this execution produced a final answer
    duration_ms : float
        Execution time in milliseconds
    memory_used_bytes : int
        Memory used during execution (if tracked)
    error : str | None
        Error message if execution failed
    timeout : bool
        Whether execution was terminated due to timeout
    final_value : Any
        The final answer value if is_final is True
    namespace : dict[str, Any]
        The execution namespace after running (for variable inspection)
    """

    output: str
    is_final: bool = False
    duration_ms: float = 0.0
    memory_used_bytes: int = 0
    error: str | None = None
    timeout: bool = False
    final_value: Any = None
    namespace: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Return True if execution succeeded without errors."""
        return self.error is None and not self.timeout


@runtime_checkable
class Executor(Protocol):
    """
    Protocol for code execution backends.

    Implementations must provide:
    - run(): Execute code and return result
    - kill(): Terminate any running execution
    - inject(): Add objects to execution namespace
    """

    def run(self, code: str) -> ExecutionResult:
        """
        Execute Python code and return the result.

        Parameters
        ----------
        code : str
            Python code to execute

        Returns
        -------
        ExecutionResult
            Result containing output, status, and metadata
        """
        ...

    def kill(self) -> None:
        """
        Terminate any currently running execution.

        This should be safe to call even if nothing is running.
        """
        ...

    def inject(self, name: str, value: Any) -> None:
        """
        Inject a value into the execution namespace.

        Parameters
        ----------
        name : str
            Name to bind the value to
        value : Any
            Value to inject
        """
        ...

    def reset(self) -> None:
        """
        Reset the executor state for a new execution.

        This clears any injected values and resets the namespace.
        """
        ...
