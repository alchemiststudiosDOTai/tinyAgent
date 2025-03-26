"""
Aider integration tool for the tinyAgent framework.

This module provides a tool for launching aider in interactive mode to make or
edit files using AI pair programming. It replaces the current process with an
aider session, which is a terminal-based interactive experience.
"""

import os
import shlex
import subprocess
from typing import Dict, Any, List, Optional

from ..logging import get_logger
from ..tool import Tool, ParamType
from ..exceptions import ToolError

# Set up logger
logger = get_logger(__name__)


def aider_exec(files: str, prompt: str) -> str:
    """
    Execute aider with files and prompt for interactive editing.
    
    This function launches aider in interactive mode for AI-assisted
    pair programming. It sets up configuration and history files in
    the tools directory and replaces the current process with aider.
    
    Args:
        files: Space-separated file paths to work with
        prompt: Message/instruction to pass to aider
        
    Returns:
        String with error message if launch fails
        (Note: normally doesn't return as it replaces the process)
        
    Raises:
        ToolError: If aider is not installed or cannot be launched
    """
    try:
        # Get the absolute path to the tools directory and related files
        # Base directory is 2 levels up from this file (core/tools/aider.py)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        tools_dir = os.path.join(base_dir, "tools")
        config_path = os.path.join(base_dir, ".aider.conf.yml")

        output_dir = os.path.join(tools_dir, "aiderOutput")
        
        logger.info(f"Launching aider with files: {files}")
        logger.debug(f"Using config from: {config_path}")
        logger.debug(f"Output directory: {output_dir}")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Build command with configuration
        cmd = [
            "aider",
            f"--config={config_path}",  # Use our config file with absolute path
            "--git",           # Use git
            "--gitignore",     # Use gitignore
            "--yes-always",    # Skip interactive prompts
            f"--chat-history-file={os.path.join(output_dir, '.aider.chat.history.md')}",
            f"--input-history-file={os.path.join(output_dir, '.aider.input.history')}",
            f"--llm-history-file={os.path.join(output_dir, '.aider.llm.history')}"
        ]
        
        # Add files (properly handle quoting)
        cmd.extend(shlex.split(files))
        
        # Add message if provided
        if prompt:
            cmd.extend(["--message", prompt])
        
        # Log the full command before execution
        logger.debug(f"Executing aider with command: {' '.join(cmd)}")
        
        # Replace current process with aider for interactive session
        os.execvp("aider", cmd)
    except FileNotFoundError:
        error_msg = "Aider is not installed or not in PATH. Please install aider to use this tool."
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error launching aider: {str(e)}"
        logger.error(error_msg)
        return error_msg


# Define the tool
aider_tool = Tool(
    name="aider",
    description="""
    Launch aider in interactive mode to make or edit files using AI pair programming.
    
    This tool launches aider in a new interactive terminal session where you can
    work with files using AI assistance. It replaces the current terminal session,
    so you'll need to restart tinyAgent after using it.
    
    Examples:
    - Edit multiple files: files="src/main.py src/utils.py", prompt="Add error handling"
    - Create new functionality: files="new_feature.py", prompt="Create a function to parse JSON"
    
    Note: Requires aider to be installed (pip install aider).
    """,
    parameters={
        "files": ParamType.STRING,  # Space-separated file paths (e.g., 'file1.py file2.py')
        "prompt": ParamType.STRING  # Required prompt to pass to aider (e.g., 'Add error handling')
    },
    func=aider_exec
)


def get_tool() -> Tool:
    """
    Return the aider tool instance for tinyAgent integration.
    
    Returns:
        Tool: The aider tool object
    """
    return aider_tool
