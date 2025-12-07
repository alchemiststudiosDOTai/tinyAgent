"""
tinyagent
A lightweight agent framework for Python.

Public surface
--------------
Agents:
    ReactAgent      - JSON tool-calling agent
    TinyCodeAgent   - Python code execution agent
    TrustLevel      - Trust level enum for TinyCodeAgent

Execution:
    Executor            - Protocol for execution backends
    ExecutionResult     - Result of code execution
    LocalExecutor       - Local restricted exec() backend
    ExecutionLimits     - Resource limits configuration
    ExecutionTimeout    - Timeout exception

Memory:
    AgentMemory     - Working memory for agent state

Observability:
    AgentLogger     - Centralized logging for agent execution

Signals:
    uncertain       - Signal uncertainty
    explore         - Signal exploration
    commit          - Signal confidence

Tools:
    tool                - Decorator to create tools (returns Tool)
    validate_tool_class - Validate a tool class

Types:
    FinalAnswer         - Final answer with metadata
    RunResult           - Complete execution result
    Finalizer           - Final answer manager

Exceptions:
    StepLimitReached     - Max steps exceeded
    MultipleFinalAnswers - Multiple final answers attempted
    InvalidFinalAnswer   - Final answer validation failed
    ToolDefinitionError  - Tool decorator validation failed
    ToolValidationError  - Tool class validation failed
"""

from .agents.code import PythonExecutor, TinyCodeAgent, TrustLevel
from .agents.react import ReactAgent
from .core import (
    FinalAnswer,
    Finalizer,
    InvalidFinalAnswer,
    MultipleFinalAnswers,
    RunResult,
    StepLimitReached,
    ToolDefinitionError,
    tool,
)
from .execution import ExecutionResult, Executor, LocalExecutor
from .limits import ExecutionLimits, ExecutionTimeout
from .memory import AgentMemory
from .observability import AgentLogger

# Lazy imports for TUI dashboards - see observability.__init__
# AgentDashboard and TermTkDashboard are available via __getattr__
from .signals import commit, explore, uncertain
from .tools import ToolValidationError, validate_tool_class

__all__ = [
    # Agents
    "ReactAgent",
    "TinyCodeAgent",
    "TrustLevel",
    # Execution
    "Executor",
    "ExecutionResult",
    "LocalExecutor",
    "PythonExecutor",  # Backwards compatibility
    "ExecutionLimits",
    "ExecutionTimeout",
    # Memory
    "AgentMemory",
    # Observability
    "AgentLogger",
    "AgentDashboard",
    "TermTkDashboard",
    # Signals
    "uncertain",
    "explore",
    "commit",
    # Tools
    "tool",
    "validate_tool_class",
    # Types
    "FinalAnswer",
    "RunResult",
    "Finalizer",
    # Exceptions
    "StepLimitReached",
    "MultipleFinalAnswers",
    "InvalidFinalAnswer",
    "ToolDefinitionError",
    "ToolValidationError",
]
