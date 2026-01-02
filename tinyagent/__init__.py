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
    AgentMemory     - Working memory for agent state (scratchpad)
    MemoryManager   - Structured conversation memory with pruning
    Step            - Base step class for memory
    SystemPromptStep - System prompt message step
    TaskStep        - User task/question step
    ActionStep      - Tool call with observation/error step
    ScratchpadStep  - Working memory notes step
    PruneStrategy   - Type alias for pruning functions
    keep_last_n_steps      - Keep last N action steps
    prune_old_observations - Truncate old observations
    no_pruning             - Identity function (no changes)

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

from dotenv import find_dotenv, load_dotenv

# Auto-load .env file on import (searches up directory tree)
env_path = find_dotenv()
if env_path:
    load_dotenv(env_path)

from .agents.code import PythonExecutor, TinyCodeAgent, TrustLevel  # noqa: E402
from .agents.react import ReactAgent  # noqa: E402
from .core import (  # noqa: E402
    FinalAnswer,
    Finalizer,
    InvalidFinalAnswer,
    MultipleFinalAnswers,
    RunResult,
    StepLimitReached,
    ToolDefinitionError,
    tool,
)
from .execution import ExecutionResult, Executor, LocalExecutor  # noqa: E402
from .limits import ExecutionLimits, ExecutionTimeout  # noqa: E402
from .memory import (  # noqa: E402
    ActionStep,
    AgentMemory,
    MemoryManager,
    PruneStrategy,
    ScratchpadStep,
    Step,
    SystemPromptStep,
    TaskStep,
    keep_last_n_steps,
    no_pruning,
    prune_old_observations,
)
from .signals import commit, explore, uncertain  # noqa: E402
from .tools import ToolValidationError, validate_tool_class  # noqa: E402

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
    "MemoryManager",
    "Step",
    "SystemPromptStep",
    "TaskStep",
    "ActionStep",
    "ScratchpadStep",
    "PruneStrategy",
    "keep_last_n_steps",
    "prune_old_observations",
    "no_pruning",
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
