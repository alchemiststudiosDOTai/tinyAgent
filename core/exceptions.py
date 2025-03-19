"""
Exceptions for the tinyAgent framework.

This module contains custom exceptions used throughout the tinyAgent framework.
"""

from typing import List, Dict, Any, Optional


class AgentRetryExceeded(Exception):
    """Exception raised when agent exceeds max retry attempts."""
    def __init__(self, message, history=None):
        self.message = message
        self.history = history or []
        super().__init__(message)


class TinyAgentError(Exception):
    """Base class for all tinyAgent exceptions."""
    pass


class ConfigurationError(TinyAgentError):
    """Exception raised for configuration-related errors."""
    pass


class ToolError(TinyAgentError):
    """Base class for tool-related errors."""
    pass


class ToolNotFoundError(ToolError):
    """Exception raised when a requested tool is not found."""
    def __init__(self, tool_name: str, available_tools: Optional[List[str]] = None):
        self.tool_name = tool_name
        self.available_tools = available_tools or []
        message = f"Tool '{tool_name}' not found"
        if available_tools:
            message += f". Available tools: {', '.join(available_tools)}"
        super().__init__(message)


class ToolExecutionError(ToolError):
    """Exception raised when a tool execution fails."""
    def __init__(self, tool_name: str, args: Dict[str, Any], error_message: str):
        self.tool_name = tool_name
        self.args = args
        self.error_message = error_message
        super().__init__(f"Error executing tool {tool_name}: {error_message}")


class RateLimitExceeded(ToolError):
    """Exception raised when a tool's rate limit is exceeded."""
    def __init__(self, tool_name: str, limit: int):
        self.tool_name = tool_name
        self.limit = limit
        super().__init__(f"Rate limit exceeded for tool '{tool_name}'. Maximum: {limit} calls")


class ParsingError(TinyAgentError):
    """Exception raised when parsing LLM responses fails."""
    def __init__(self, content: str, details: str = None):
        self.content = content
        self.details = details
        message = "Failed to parse LLM response"
        if details:
            message += f": {details}"
        super().__init__(message)


class OrchestratorError(TinyAgentError):
    """Exception raised for orchestrator-related errors."""
    pass


class AgentNotFoundError(OrchestratorError):
    """Exception raised when a requested agent is not found."""
    def __init__(self, agent_id: str, available_agents: Optional[List[str]] = None):
        self.agent_id = agent_id
        self.available_agents = available_agents or []
        message = f"Agent '{agent_id}' not found"
        if available_agents:
            message += f". Available agents: {', '.join(available_agents)}"
        super().__init__(message)
