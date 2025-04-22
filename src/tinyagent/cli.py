#!/usr/bin/env python
"""
tinyAgent - A simple yet powerful framework for building LLM-powered agents.

This is the main entry point for the tinyAgent framework. It provides access to 
all the core components of the framework through a clean, simple API.
"""

# Load environment variables first
from dotenv import load_dotenv
load_dotenv() 

from tinyagent import (
    # Core components
    Agent, get_llm, Tool, ParamType, tool,
    
    # Exception classes
    TinyAgentError, ConfigurationError, 
    ToolError, ToolNotFoundError, ToolExecutionError,
    RateLimitExceeded, ParsingError, 
    AgentRetryExceeded, OrchestratorError, AgentNotFoundError,
    
    # Factory components
    AgentFactory, DynamicAgentFactory, Orchestrator, TaskStatus,
    
    # Utilities
    configure_logging, get_logger, load_config, get_config_value,
    Colors, Spinner, CLI, run_chat_mode,
    
    # Version
    __version__
)

# Built-in tools
from tinyagent.tools import (
    anon_coder_tool,
    llm_serializer_tool,
    brave_web_search_tool,
    ripgrep_tool,
    aider_tool,
    load_external_tools
)

# Run CLI if executed directly
if __name__ == "__main__":
    # Call the core CLI implementation
    CLI()
