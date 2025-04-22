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

# Core components
from .agent import Agent, get_llm, tiny_agent
from .tool import Tool, ParamType
from .decorators import tool
from .exceptions import (
    TinyAgentError, ConfigurationError, 
    ToolError, ToolNotFoundError, ToolExecutionError,
    RateLimitExceeded, ParsingError, 
    AgentRetryExceeded, OrchestratorError, AgentNotFoundError
)

# Factory components
from .factory import (
    AgentFactory, DynamicAgentFactory, 
    Orchestrator, TaskStatus
)

# Logging utilities
from .logging import configure_logging, get_logger

# Configuration utilities
from .config import load_config, get_config_value

# CLI utilities
from .cli import (
    main as CLI,  # Use main function as CLI for backward compatibility
    Colors, 
    Spinner
)

# Chat mode
from .chat import run_chat_mode

# Public exports
__all__ = [
    # Core components
    'Agent', 'get_llm', 
    'Tool', 'ParamType',
    'tool',
    
    # Exception classes
    'TinyAgentError',
    'ConfigurationError',
    'ToolError', 'ToolNotFoundError', 'ToolExecutionError',
    'RateLimitExceeded',
    'ParsingError',
    'AgentRetryExceeded',
    'OrchestratorError', 'AgentNotFoundError',
    
    # Factory components
    'AgentFactory', 'DynamicAgentFactory',
    'Orchestrator', 'TaskStatus',
    
    # Utilities
    'configure_logging', 'get_logger',
    'load_config', 'get_config_value',
    'Colors', 'Spinner', 'CLI',
    'run_chat_mode',
    
    # Version
    '__version__'
]
