"""
AgentFactory module for managing tool and agent creation with rate limiting.

This module provides a factory class for creating, registering, and managing tools
and agents with built-in rate limiting capabilities.
"""

import inspect
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

if TYPE_CHECKING:
    from ..agent import Agent

from ..config import get_config_value, load_config
from ..exceptions import RateLimitExceeded, ToolNotFoundError
from ..logging import get_logger
from ..tool import ParamType, Tool

# Set up logger
logger = get_logger(__name__)

# Define a generic type variable for better type hints
T = TypeVar("T")


class AgentFactory:
    """
    Factory for creating and managing tools and agents with rate limiting.

    This class implements the Singleton pattern to ensure only one instance exists,
    providing centralized tool registration and rate limit enforcement across
    the application.

    Attributes:
        config: Configuration dictionary
        _tools: Dictionary of registered tools
        _call_counts: Dictionary tracking tool usage
        _rate_limits: Dictionary of rate limits from configuration
        _global_limit: Global rate limit applied to all tools
    """

    _instance = None  # Singleton instance

    @classmethod
    def get_instance(cls: Type[T], config: Optional[Dict[str, Any]] = None) -> T:
        """
        Get or create the singleton factory instance.

        Args:
            config: Optional configuration dictionary

        Returns:
            The singleton AgentFactory instance
        """
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the factory with optional configuration.

        Args:
            config: Optional configuration dictionary
        """
        # Load configuration if not provided
        if config is None:
            self.config = load_config()
        else:
            self.config = config

        # Tool registry
        self._tools: Dict[str, Tool] = {}
        # Call count tracking
        self._call_counts: Dict[str, int] = {}

        # Load rate limits from config with default of 30
        self._rate_limits = self._load_rate_limits(self.config)
        # Global rate limit (default: 30)
        self._global_limit = self._rate_limits.get("global_limit", 30)

        logger.debug(
            f"Initialized AgentFactory with global rate limit: {self._global_limit}"
        )

    def _load_rate_limits(self, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Load rate limits from configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Dictionary of rate limits
        """
        if not config:
            return {"global_limit": 30}

        # Get rate limits from config or use default
        limits = get_config_value(config, "rate_limits", {})
        if not limits:
            limits = {"global_limit": 30}
        elif "global_limit" not in limits:
            limits["global_limit"] = 30

        logger.debug(f"Loaded rate limits: {limits}")
        return limits

    def create_tool(
        self,
        name: str,
        description: str,
        func: Callable,
        rate_limit: Optional[int] = None,
    ) -> Tool:
        """
        Create and register a new tool.

        This method creates a Tool instance from a function, automatically extracting
        parameter types from the function's type hints.

        Args:
            name: Tool name (lowercase, no spaces)
            description: Tool description
            func: Function to execute when the tool is called
            rate_limit: Optional rate limit override for this tool

        Returns:
            The created Tool instance

        Raises:
            ValueError: If the tool name is invalid
        """
        # Validate tool name
        if not name or not isinstance(name, str):
            raise ValueError("Tool name must be a non-empty string")
        if not name.islower() or " " in name:
            raise ValueError("Tool name must be lowercase with no spaces")

        # Extract parameters from function signature
        sig = inspect.signature(func)
        parameters = {}

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            # Map Python type hints to ParamType
            if param.annotation is int:
                param_type = ParamType.INTEGER
            elif param.annotation is float:
                param_type = ParamType.FLOAT
            elif param.annotation is str:
                param_type = ParamType.STRING
            else:
                param_type = ParamType.ANY

            parameters[param_name] = param_type

        # Create tool instance
        tool = Tool(
            name=name, description=description, parameters=parameters, func=func
        )

        # Add rate limit metadata if provided
        if rate_limit is not None:
            tool.rate_limit = rate_limit

        # Register the tool
        self._tools[tool.name] = tool
        self._call_counts[tool.name] = 0

        logger.info(f"Created and registered tool: {tool.name}")
        return tool

    def register_tool(self, tool: Tool) -> Tool:
        """
        Register an existing tool with the factory.

        Args:
            tool: Tool instance to register

        Returns:
            The registered Tool instance
        """
        self._tools[tool.name] = tool
        self._call_counts[tool.name] = 0
        logger.info(f"Registered tool: {tool.name}")
        return tool

    def create_agent(
        self,
        tools: Optional[List[Union[Tool, Callable]]] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> "Agent":
        """
        Create a new agent with specified tools.

        This method creates an Agent instance with the specified tools. If a tool
        is provided as a function, it will be converted to a Tool instance.

        Args:
            tools: List of Tool instances or callable functions
            model: Optional model name to use for the agent
            **kwargs: Additional keyword arguments to pass to the Agent constructor (e.g., trace_this_agent).

        Returns:
            The created Agent instance
        """
        # Import Agent here to avoid circular imports
        from ..agent import Agent, TracedAgent  # Keep both imports

        # --- ADDED: Import tracer provider status ---
        from ..observability.tracer import _tracer_provider, configure_tracing

        # --- MODIFIED: Logic to determine agent class ---
        should_trace_explicit = kwargs.pop(
            "trace_this_agent", None
        )  # Get explicit flag, default None

        # Ensure tracing is configured if not already (needed for check below)
        if _tracer_provider is None:
            configure_tracing()  # Use default config

        # Determine if tracing is globally active
        is_tracing_globally_active = (
            _tracer_provider is not None
            and type(_tracer_provider).__name__ != "NoOpTracerProvider"
        )

        if should_trace_explicit is True:
            logger.info("Creating TracedAgent instance (explicitly requested).")
            agent = TracedAgent(model=model, **kwargs)
        elif should_trace_explicit is False:
            logger.info("Creating standard Agent instance (explicitly requested off).")
            agent = Agent(model=model, **kwargs)
        elif is_tracing_globally_active:
            # Default case: trace_this_agent not specified, but tracing is globally ON
            logger.info("Creating TracedAgent instance (tracing globally active).")
            agent = TracedAgent(model=model, **kwargs)
        else:
            # Default case: trace_this_agent not specified, tracing globally OFF
            logger.info("Creating standard Agent instance (tracing globally inactive).")
            agent = Agent(model=model, **kwargs)
        # --- END MODIFIED LOGIC ---

        # Register existing factory tools with the agent
        for tool_name, tool in self._tools.items():
            if (
                tool_name != "chat"
            ):  # Skip the built-in chat tool, as Agent already adds it
                agent.create_tool(
                    name=tool.name,
                    description=tool.description,
                    func=tool.func,
                    parameters=tool.parameters,
                )

        # Register any additional tools provided
        if tools:
            for tool in tools:
                if isinstance(tool, Tool):
                    # Register with factory first
                    self.register_tool(tool)
                    # Register with agent
                    agent.create_tool(
                        name=tool.name,
                        description=tool.description,
                        func=tool.func,
                        parameters=tool.parameters,
                    )
                elif callable(tool):
                    # Create Tool instance from function
                    func_name = getattr(tool, "__name__", "anonymous_function").lower()
                    tool_desc = tool.__doc__ or f"Tool for {func_name}"
                    # Register with factory
                    created_tool = self.create_tool(
                        name=func_name, description=tool_desc, func=tool
                    )
                    # Register with agent
                    agent.create_tool(
                        name=func_name,
                        description=tool_desc,
                        func=tool,
                        parameters=created_tool.parameters,
                    )

        logger.info(f"Created agent with {len(agent.get_available_tools())} tools")

        return agent

    def get_tool_metadata(self, name: str) -> Tool:
        """
        Get a tool by name WITHOUT incrementing the counter.

        This method is used to access tool metadata (description, parameters)
        without counting against the rate limit.

        Args:
            name: Name of the tool to retrieve

        Returns:
            The requested Tool instance

        Raises:
            ToolNotFoundError: If the tool is not registered
        """
        if name not in self._tools:
            raise ToolNotFoundError(f"Tool '{name}' not registered")

        return self._tools[name]

    def execute_tool(self, name: str, *args, **kwargs) -> Any:
        """
        Execute a tool and increment its usage counter.

        This method should be used when actually executing a tool function,
        not just accessing its metadata.

        Args:
            name: Name of the tool to execute
            *args: Positional arguments to pass to the tool
            **kwargs: Keyword arguments to pass to the tool

        Returns:
            The result of the tool execution

        Raises:
            ToolNotFoundError: If the tool is not registered
            RateLimitExceeded: If the tool's rate limit has been exceeded
        """
        if name not in self._tools:
            raise ToolNotFoundError(f"Tool '{name}' not registered")

        # Get tool-specific limit or use global
        tool_limit = self._get_tool_limit(name)

        # Block execution if limit exceeded
        if (
            tool_limit is not None
            and tool_limit > 0
            and self._call_counts[name] >= tool_limit
        ):
            logger.warning(
                f"Rate limit exceeded for tool '{name}': {self._call_counts[name]}/{tool_limit}"
            )
            raise RateLimitExceeded(
                f"Tool '{name}' call limit of {tool_limit} exceeded", limit=tool_limit
            )

        # Get the tool and execute it
        tool = self._tools[name]
        result = tool(*args, **kwargs)

        # Only increment counter after successful execution
        self._call_counts[name] += 1
        limit_display = tool_limit if tool_limit is not None else "∞"
        logger.debug(f"Tool '{name}' usage: {self._call_counts[name]}/{limit_display}")

        return result

    def get_tool(self, name: str) -> Tool:
        """
        Get a tool by name with rate limit checks.

        This method is maintained for backward compatibility but should be
        avoided in favor of get_tool_metadata() and execute_tool().

        Args:
            name: Name of the tool to retrieve

        Returns:
            The requested Tool instance

        Raises:
            ToolNotFoundError: If the tool is not registered
            RateLimitExceeded: If the tool's rate limit has been exceeded
        """
        # Just get metadata - we'll count when the tool is actually executed
        return self.get_tool_metadata(name)

    def _get_tool_limit(self, tool_name: str) -> Optional[int]:
        """
        Get rate limit for a specific tool.

        This method retrieves the rate limit for a tool, checking in order:
        1. Tool's own rate_limit attribute
        2. Tool-specific rate limit in configuration
        3. Global rate limit

        Args:
            tool_name: Name of the tool

        Returns:
            The rate limit for the tool (or -1 for unlimited)
        """
        # First check if tool has a specific rate limit set
        tool = self._tools.get(tool_name)
        if tool and hasattr(tool, "rate_limit") and tool.rate_limit is not None:
            return tool.rate_limit

        # Otherwise check config
        tool_limits = self._rate_limits.get("tool_limits", {})
        return tool_limits.get(tool_name, self._global_limit)

    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of tool usage.

        Returns:
            Dictionary with current tool usage statistics
        """
        status = {"global_limit": self._global_limit, "tools": {}}

        for name, count in self._call_counts.items():
            limit = self._get_tool_limit(name)
            status["tools"][name] = {
                "calls": count,
                "limit": limit,
                "remaining": (
                    max(0, limit - count) if limit is not None and limit > 0 else -1
                ),
            }

        return status

    def reset_counts(self) -> None:
        """
        Reset all call counts.

        This is useful for CLI context or when starting a new session.
        """
        self._call_counts = {name: 0 for name in self._call_counts}
        logger.info("Reset all tool call counts")

    def get_tracked_tool(self, name: str) -> Tool:
        """
        Get a tool that is tracked only when actually executed.

        This method creates a new Tool instance that wraps the original
        tool's function in a way that calls execute_tool() instead of
        directly calling the function, ensuring proper usage tracking.

        Args:
            name: Name of the tool to create a tracked version of

        Returns:
            A Tool instance that tracks usage

        Raises:
            ToolNotFoundError: If the tool is not registered
        """
        if name not in self._tools:
            raise ToolNotFoundError(f"Tool '{name}' not registered")

        original_tool = self.get_tool_metadata(name)

        # Create a proxy function that uses execute_tool() for tracking
        def proxy_func(*args, **kwargs):
            # Only count when actually executed
            return self.execute_tool(name, *args, **kwargs)

        # Create a new tool with the same metadata but tracked function
        tracked_tool = Tool(
            name=original_tool.name,
            description=original_tool.description,
            parameters=original_tool.parameters,
            func=proxy_func,
        )

        # Copy any custom attributes
        if hasattr(original_tool, "rate_limit"):
            tracked_tool.rate_limit = original_tool.rate_limit

        return tracked_tool

    def list_tools(self) -> Dict[str, Tool]:
        """List all registered tools."""
        return self._tools.copy()
