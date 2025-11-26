"""
tinyagent.execution
Executor protocol and implementations for sandboxed code execution.

Public surface
--------------
Executor         – Protocol
ExecutionResult  – dataclass
LocalExecutor    – class
"""

from .local import LocalExecutor
from .protocol import ExecutionResult, Executor

__all__ = ["Executor", "ExecutionResult", "LocalExecutor"]
