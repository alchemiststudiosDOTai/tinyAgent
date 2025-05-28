"""
Core components for the tinyAgent framework.

This package contains the core components of the tinyAgent framework, including
the Agent class, Tool framework, configuration management, and utilities.
"""

try:
    from ._version import __version__
except ImportError:
    # This happens during development or if setuptools_scm is not installed
    __version__ = "0.0.0.dev0"  # Default or placeholder version

from .tool import Tool, ParamType
from .decorators import tool
from .exceptions import (
    TinyAgentError, ConfigurationError,
    ToolError, ToolNotFoundError, ToolExecutionError,
    RateLimitExceeded, ParsingError,
    AgentRetryExceeded, OrchestratorError, AgentNotFoundError
)
from .react.react_agent import ReactAgent

__all__ = [
    'Tool', 'ParamType', 'tool', 'ReactAgent',
    'TinyAgentError', 'ConfigurationError', 'ToolError',
    'ToolNotFoundError', 'ToolExecutionError', 'RateLimitExceeded',
    'ParsingError', 'AgentRetryExceeded', 'OrchestratorError',
    'AgentNotFoundError', '__version__'
]
