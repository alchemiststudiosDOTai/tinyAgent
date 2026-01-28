"""
tinyagent.execution.local
Local executor using restricted exec() for trusted code execution.

Public surface
--------------
LocalExecutor  – class
"""

from __future__ import annotations

import ast
import builtins
import contextlib
import io
import time
from typing import Any

from ..utils.limits import ExecutionLimits, ExecutionTimeout
from .protocol import ExecutionResult

__all__ = ["LocalExecutor"]


class FinalResult:
    """Sentinel class for final_answer() results."""

    __slots__ = ("value", "verified_by")

    def __init__(self, value: Any, verified_by: str | None = None):
        self.value = value
        self.verified_by = verified_by


class LocalExecutor:
    """
    Local executor using restricted exec() for trusted code execution.

    This executor runs code in the same process with restricted builtins
    and controlled imports. Suitable for trusted tools and fast iteration.

    Parameters
    ----------
    allowed_imports : set[str] | None
        Set of module names allowed to be imported (e.g., {"math", "json"})
    limits : ExecutionLimits | None
        Resource limits for execution (timeout, output size, etc.)
    """

    SAFE_BUILTINS = frozenset(
        {
            "abs",
            "all",
            "any",
            "bool",
            "callable",
            "chr",
            "dict",
            "dir",
            "divmod",
            "enumerate",
            "filter",
            "float",
            "format",
            "frozenset",
            "getattr",
            "hasattr",
            "hash",
            "id",
            "int",
            "isinstance",
            "issubclass",
            "iter",
            "len",
            "list",
            "map",
            "max",
            "min",
            "next",
            "oct",
            "ord",
            "pow",
            "print",
            "range",
            "repr",
            "reversed",
            "round",
            "set",
            "slice",
            "sorted",
            "str",
            "sum",
            "tuple",
            "type",
            "vars",
            "zip",
        }
    )

    def __init__(
        self,
        allowed_imports: set[str] | None = None,
        limits: ExecutionLimits | None = None,
    ):
        self._allowed_imports = set(allowed_imports or ())
        self._limits = limits or ExecutionLimits()
        self._namespace: dict[str, Any] = {}
        self._reset_namespace()

    def _reset_namespace(self) -> None:
        """Reset namespace to initial state with safe builtins."""
        safe_builtins = {k: getattr(builtins, k) for k in self.SAFE_BUILTINS}
        safe_builtins["__import__"] = self._safe_import
        self._namespace = {"__builtins__": safe_builtins}
        # Inject final_answer function
        self._namespace["final_answer"] = self._final_answer

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
        self._namespace[name] = value

    def reset(self) -> None:
        """Reset the executor state for a new execution."""
        self._reset_namespace()

    def kill(self) -> None:
        """
        Terminate any running execution.

        For LocalExecutor, this is a no-op since execution is synchronous.
        The timeout mechanism handles termination.
        """
        pass

    def run(self, code: str) -> ExecutionResult:
        """
        Execute Python code in sandboxed environment with timeout.

        Parameters
        ----------
        code : str
            Python code to execute

        Returns
        -------
        ExecutionResult
            Result containing output, status, and metadata
        """
        start_time = time.perf_counter()

        # Validate imports before execution
        try:
            self._check_imports(code)
        except RuntimeError as e:
            return ExecutionResult(
                output="",
                error=str(e),
                duration_ms=(time.perf_counter() - start_time) * 1000,
            )

        # Capture stdout
        stdout_buffer = io.StringIO()

        try:
            with self._limits.timeout_context():
                with contextlib.redirect_stdout(stdout_buffer):
                    # Execute in controlled namespace
                    exec(code, self._namespace)  # nosec B102

            # Check for final answer
            if "_final_result" in self._namespace and isinstance(
                self._namespace["_final_result"], FinalResult
            ):
                final_result = self._namespace["_final_result"]
                output = stdout_buffer.getvalue().strip()
                output, _ = self._limits.truncate_output(output)

                return ExecutionResult(
                    output=output,
                    is_final=True,
                    final_value=final_result.value,
                    duration_ms=(time.perf_counter() - start_time) * 1000,
                    namespace=dict(self._namespace),
                )

            # Return stdout output
            output = stdout_buffer.getvalue().strip()
            output, _ = self._limits.truncate_output(output)

            return ExecutionResult(
                output=output,
                is_final=False,
                duration_ms=(time.perf_counter() - start_time) * 1000,
                namespace=dict(self._namespace),
            )

        except ExecutionTimeout as e:
            return ExecutionResult(
                output=stdout_buffer.getvalue().strip(),
                timeout=True,
                error=str(e),
                duration_ms=(time.perf_counter() - start_time) * 1000,
            )
        except Exception as e:
            return ExecutionResult(
                output=stdout_buffer.getvalue().strip(),
                error=f"{type(e).__name__}: {e}",
                duration_ms=(time.perf_counter() - start_time) * 1000,
            )

    def _safe_import(
        self,
        name: str,
        globals_: dict | None = None,
        locals_: dict | None = None,
        fromlist: tuple = (),
        level: int = 0,
    ) -> Any:
        """Controlled import function that only allows whitelisted modules."""
        module_name = name.split(".")[0]
        if module_name not in self._allowed_imports:
            raise RuntimeError(f"Import '{name}' not allowed")
        return __import__(name, globals_, locals_, fromlist, level)

    def _final_answer(self, value: Any, *, verified_by: str | None = None) -> Any:
        """
        Store final answer in the namespace.

        Parameters
        ----------
        value : Any
            The final answer value
        verified_by : str | None
            Optional verification rationale

        Returns
        -------
        Any
            The value (for convenience in expressions)
        """
        self._namespace["_final_result"] = FinalResult(value, verified_by)
        return value

    def _check_imports(self, code: str) -> None:
        """
        Validate all imports in code against whitelist.

        Parameters
        ----------
        code : str
            Python code to check

        Raises
        ------
        RuntimeError
            If an unauthorized import is found
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise RuntimeError(f"Syntax error in code: {e}") from e

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    if module not in self._allowed_imports:
                        raise RuntimeError(f"Import '{alias.name}' not allowed")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split(".")[0]
                    if module not in self._allowed_imports:
                        raise RuntimeError(f"Import from '{node.module}' not allowed")
