"""
MCP (Model Context Protocol) integration for tinyAgent.

This package provides integration with MCP servers, allowing tinyAgent
to access external tools and resources through the Model Context Protocol.
"""

from .manager import McpServerManager, call_mcp_tool, ensure_mcp_server

__all__ = ["McpServerManager", "ensure_mcp_server", "call_mcp_tool"]
