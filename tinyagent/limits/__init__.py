"""
tinyagent.limits
Resource boundaries and timeout management for code execution.

Public surface
--------------
ExecutionLimits  – dataclass
TimeoutError     – exception
"""

from .boundaries import ExecutionLimits, ExecutionTimeout

__all__ = ["ExecutionLimits", "ExecutionTimeout"]
