"""
MCP (Model Context Protocol) server management.

This module provides classes and functions to manage the MCP server process
and communicate with it, allowing the use of MCP tools within tinyAgent.
"""

import os
import time
import json
import subprocess
from typing import Dict, Any, Optional, List, Union

from ..logging import get_logger
from ..exceptions import ConfigurationError

# Set up logger
logger = get_logger(__name__)

# Global variables for MCP server management
_mcp_server_process = None
_mcp_initialized = False


class McpServerManager:
    """
    Manages MCP server processes and communication.
    
    This class handles starting, stopping, and communicating with MCP servers.
    It ensures that the server is running and provides methods to call 
    MCP tools.
    
    Attributes:
        server_process: Subprocess object representing the MCP server process
        initialized: Flag indicating if the server is initialized
        available: Flag indicating if the MCP server is available
    """
    
    def __init__(self):
        """Initialize the MCP server manager."""
        self.server_process = None
        self.initialized = False
        self.available = False  # Flag to indicate if MCP server is available
        self.brave_api_key = os.getenv('BRAVE', '')
        
    def start_server(self) -> bool:
        """
        Start the MCP server process.
        
        This method starts the MCP server as a subprocess and ensures it's 
        ready to receive commands.
        
        Returns:
            bool: True if the server started successfully, False otherwise
        """
        if self.server_process is not None and self.server_process.poll() is None:
            logger.info("MCP server is already running")
            self.available = True
            return True
            
        # Determine the MCP directory
        mcp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "mcp")
            
        if not os.path.isdir(mcp_dir):
            logger.error(f"MCP directory not found at {mcp_dir}")
            self.available = False
            return False
            
        # Check for API key when needed
        if not self.brave_api_key:
            logger.warning("BRAVE environment variable not set, MCP search tools will be disabled")
            
        try:
            # Start the MCP server process
            self.server_process = subprocess.Popen(
                ['node', os.path.join(mcp_dir, 'build', 'index.js')],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env={**os.environ, 'BRAVE': self.brave_api_key}
            )
            
            # Give the server a moment to start up
            time.sleep(1)
            
            if self.server_process.poll() is not None:
                stderr_output = self.server_process.stderr.read()
                logger.error(f"MCP server failed to start: {stderr_output}")
                self.available = False
                return False
                
            logger.info("MCP server started successfully")
            self.initialized = True
            self.available = True
            return True
            
        except Exception as e:
            logger.error(f"Error starting MCP server: {str(e)}")
            self.available = False
            return False
            
    def stop_server(self) -> None:
        """
        Stop the MCP server process.
        
        This method stops the MCP server process if it's running.
        """
        if self.server_process is None:
            return
            
        try:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                logger.warning("Had to forcefully kill MCP server process")
                
            self.server_process = None
            self.initialized = False
            logger.info("MCP server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping MCP server: {str(e)}")
            
    def ensure_server_running(self) -> bool:
        """
        Ensure the MCP server is running and ready.
        
        This method checks if the server is running and starts it if not.
        
        Returns:
            bool: True if the server is running, False otherwise
        """
        # If server isn't initialized or has terminated, start it
        if self.server_process is None or self.server_process.poll() is not None:
            self.initialized = False
            self.server_process = None
            return self.start_server()
        
        # If we have a server process and it's running, we're good
        self.available = True
        return True
        
    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        Call an MCP tool with the given arguments.
        
        Args:
            tool_name: Name of the MCP tool to call
            args: Dictionary of arguments to pass to the tool
            
        Returns:
            The result of the tool call
            
        Raises:
            RuntimeError: If the MCP server is not running or returns an error
        """
        try:
            # Make sure the server is running
            if not self.ensure_server_running():
                return f"Error: MCP server is not available. Tool '{tool_name}' cannot be used."
            
            # Format request using the MCP tools/call format
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": args
                },
                "id": 1
            }

            logger.debug(f"Sending request to MCP server: {json.dumps(request)}")
            
            # Send request to MCP server
            self.server_process.stdin.write(json.dumps(request) + "\n")
            self.server_process.stdin.flush()
            
            # Read response with timeout
            response_str = ""
            start_time = time.time()
            while time.time() - start_time < 10:  # 10 second timeout
                if self.server_process.stdout.readable():
                    line = self.server_process.stdout.readline().strip()
                    if line:
                        logger.debug(f"Got response from MCP server: {line[:100]}...")
                        response_str = line
                        break
                        
                # Check stderr for errors
                if self.server_process.stderr.readable():
                    err_line = self.server_process.stderr.readline().strip()
                    if err_line:
                        logger.debug(f"MCP server stderr: {err_line}")
                        
                time.sleep(0.1)
            
            if not response_str:
                raise RuntimeError("MCP server timeout")
                
            # Try to parse the response
            try:
                response = json.loads(response_str)
                
                if "error" in response:
                    error_msg = response["error"].get("message", "Unknown error")
                    logger.error(f"MCP server returned error: {error_msg}")
                    raise RuntimeError(error_msg)
                    
                if "result" in response and "content" in response["result"]:
                    content = response["result"]["content"]
                    if content and isinstance(content, list) and len(content) > 0:
                        if "text" in content[0]:
                            return content[0]["text"]
                        return json.dumps(content)
                    
                # If we reached here, return the raw result
                return json.dumps(response.get("result", {}))
                
            except json.JSONDecodeError:
                # If we can't parse as JSON but have a response, return it anyway
                logger.warning("Couldn't parse response as JSON, returning raw response")
                return response_str
                
            return response_str
            
        except Exception as e:
            logger.error(f"Error in call_tool: {e}")
            # If we caught an exception but there's still a response, return it
            if "response_str" in locals() and response_str:
                logger.debug("Returning raw response despite error")
                return response_str
            raise RuntimeError(f"MCP tool call failed: {str(e)}")
            
    def __enter__(self) -> 'McpServerManager':
        """
        Start the MCP server when entering a context.
        
        Returns:
            The McpServerManager instance
        """
        self.start_server()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop the MCP server when exiting a context."""
        self.stop_server()


# Global manager instance for backward compatibility
_manager = McpServerManager()


def ensure_mcp_server() -> bool:
    """
    Ensure the MCP server is running and ready.
    
    This function is a wrapper around the McpServerManager.ensure_server_running
    method for backward compatibility.
    
    Returns:
        bool: True if the server is running, False otherwise
    """
    global _manager
    return _manager.ensure_server_running()


def call_mcp_tool(tool_name: str, args: Dict[str, Any], _: Any) -> Any:
    """
    Call an MCP tool with the given arguments.
    
    This function is a wrapper around the McpServerManager.call_tool method 
    for backward compatibility.
    
    Args:
        tool_name: Name of the MCP tool to call
        args: Dictionary of arguments to pass to the tool
        _: Unused parameter for backward compatibility
        
    Returns:
        The result of the tool call
        
    Raises:
        RuntimeError: If the MCP server is not running or returns an error
    """
    global _manager
    return _manager.call_tool(tool_name, args)


def load_mcp_tools() -> List[Any]:
    """
    Load tools from MCP servers.
    
    This function is a wrapper around the MCP server initialization for 
    backward compatibility.
    
    Returns:
        Empty list (the actual tools are registered elsewhere)
    """
    global _manager
    
    # Try to start the server, but don't fail if it doesn't start
    _manager.start_server()
    
    return []


def cleanup_mcp_server() -> None:
    """
    Cleanup MCP server process on exit.
    
    This function is a wrapper around the McpServerManager.stop_server method
    for backward compatibility.
    """
    global _manager
    _manager.stop_server()