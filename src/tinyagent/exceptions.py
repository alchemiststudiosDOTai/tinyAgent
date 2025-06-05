"""
Exceptions for the tinyAgent framework.

This module contains custom exceptions used throughout the tinyAgent framework.
"""

from typing import Any, Dict, List, Optional


class AgentRetryExceeded(Exception):
    """Exception raised when agent exceeds max retry attempts."""

    # Error codes for different types of failures
    ERROR_UNKNOWN = "ERR_UNKNOWN"
    ERROR_NO_VALID_TOOL = "ERR_NO_VALID_TOOL"
    ERROR_INVALID_RESPONSE_FORMAT = "ERR_INVALID_RESPONSE_FORMAT"
    ERROR_PARSING_FAILED = "ERR_PARSING_FAILED"
    ERROR_TOOL_EXECUTION_FAILED = "ERR_TOOL_EXECUTION_FAILED"
    ERROR_HTTP_ERROR = "ERR_HTTP_ERROR"
    ERROR_API_REQUEST = "ERR_API_REQUEST"

    def __init__(self, message, history=None, error_code=None):
        self.message = message
        self.history = history or []

        # Determine error code from history if not provided
        if error_code is None and history:
            # Get most common error from history
            errors = [
                attempt.get("error", "") for attempt in history if "error" in attempt
            ]
            if errors:
                if any("No valid tool found" in err for err in errors):
                    self.error_code = self.ERROR_NO_VALID_TOOL
                elif any("Invalid response format" in err for err in errors):
                    self.error_code = self.ERROR_INVALID_RESPONSE_FORMAT
                elif any("Tool execution failed" in err for err in errors):
                    self.error_code = self.ERROR_TOOL_EXECUTION_FAILED
                elif any("HTTP error" in err for err in errors):
                    self.error_code = self.ERROR_HTTP_ERROR
                elif any("API request" in err for err in errors):
                    self.error_code = self.ERROR_API_REQUEST
                elif any("Invalid or empty response format" in err for err in errors):
                    self.error_code = self.ERROR_PARSING_FAILED
                else:
                    self.error_code = self.ERROR_UNKNOWN
            else:
                self.error_code = self.ERROR_UNKNOWN
        else:
            self.error_code = error_code or self.ERROR_UNKNOWN

        # Add error code to message
        message_with_code = f"[{self.error_code}] {message}"
        super().__init__(message_with_code)

    def __str__(self):
        return f"[{self.error_code}] {self.message}"


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
        super().__init__(
            f"Rate limit exceeded for tool '{tool_name}'. Maximum: {limit} calls"
        )


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
