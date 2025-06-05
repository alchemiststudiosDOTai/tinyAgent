"""
Ripgrep search tool for the tinyAgent framework.

This module provides a tool for searching files using ripgrep (rg), a fast and
feature-rich search tool. It allows searching for patterns in files with various
options and can return results in plain text or structured JSON format.
"""

import json
import subprocess

from ..logging import get_logger
from ..tool import ParamType, Tool

# Set up logger
logger = get_logger(__name__)


def ripgrep_search(
    pattern: str, path: str, flags: str = "", json_output: bool = False
) -> str:
    """
    Execute ripgrep (rg) search with the given parameters.

    This function runs the ripgrep command-line tool to search for patterns in files.
    It supports various options and can return results in plain text or structured
    JSON format.

    Args:
        pattern: Search pattern (regular expression)
        path: Path to search in (file or directory)
        flags: Additional ripgrep flags (e.g., "-i -A 2")
        json_output: Whether to return structured JSON output

    Returns:
        String containing search results or JSON string with results

    Raises:
        ToolError: If ripgrep is not installed or an error occurs during execution
    """
    cmd = ["rg", pattern]

    # Add any additional flags
    if flags:
        cmd.extend(flags.split())

    # Add JSON output flag if requested
    if json_output:
        cmd.append("--json")

    # Add path to search
    cmd.append(path)

    logger.debug(f"Executing ripgrep command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,  # Don't raise exception if rg returns non-zero exit code
        )

        # Handle potential errors
        if (
            result.returncode != 0 and result.returncode != 1
        ):  # 1 means no matches, which is ok
            error_msg = f"Ripgrep error (code {result.returncode}): {result.stderr}"
            logger.error(error_msg)
            return error_msg

        # Return output
        if json_output:
            # Parse and re-serialize to ensure valid JSON
            try:
                # Filter out empty lines before parsing
                lines = [line for line in result.stdout.strip().split("\n") if line]
                if not lines:
                    return json.dumps([])

                parsed = [json.loads(line) for line in lines]
                return json.dumps(parsed, indent=2)
            except json.JSONDecodeError as e:
                error_msg = f"Error parsing JSON output: {str(e)}"
                logger.error(error_msg)
                return error_msg
        else:
            return result.stdout or "No matches found"

    except FileNotFoundError:
        error_msg = "Ripgrep (rg) is not installed or not in PATH. Please install ripgrep to use this tool."
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Failed to execute ripgrep: {str(e)}"
        logger.error(error_msg)
        return error_msg


# Define the tool
ripgrep_tool = Tool(
    name="ripgrep",
    description="""
    Search for patterns in files using ripgrep (rg).

    This tool uses the fast, feature-rich ripgrep search utility to find patterns
    in files. It supports regular expressions and various search options.

    Examples:
    - Find all occurrences of "function" in Python files: pattern="function", path="*.py"
    - Case-insensitive search with 2 lines of context: pattern="error", path="logs/", flags="-i -A 2"
    - Get structured JSON output: pattern="TODO", path="src/", json_output=true

    Note: Requires ripgrep (rg) to be installed on the system.
    """,
    parameters={
        "pattern": ParamType.STRING,
        "path": ParamType.STRING,
        "flags": ParamType.STRING,
        "json_output": ParamType.ANY,
    },
    func=ripgrep_search,
)


def get_tool() -> Tool:
    """
    Return the ripgrep tool instance for tinyAgent integration.

    Returns:
        Tool: The ripgrep tool object
    """
    return ripgrep_tool
