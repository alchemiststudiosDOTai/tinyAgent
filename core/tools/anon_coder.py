"""
Anonymous Python code execution tool for the tinyAgent framework.

This module provides a tool for generating and executing Python code safely.
It includes security checks, error handling, and execution in a controlled
environment to prevent harmful operations while allowing useful code execution.
"""

import os
import sys
import subprocess
import tempfile
import re
import ast
import traceback
from typing import List, Dict, Any, Optional, Set

from ..logging import get_logger
from ..tool import Tool, ParamType
from ..exceptions import ToolError

# Set up logger
logger = get_logger(__name__)

# Define constants
DEFAULT_TIMEOUT = 10  # seconds
MAX_TIMEOUT = 60  # maximum allowed timeout in seconds
MAX_CODE_SIZE = 10000  # reduced maximum code size in characters for safety


class CodeExecutionError(Exception):
    """Exception raised for errors during code execution."""
    pass


def validate_code(code: str) -> None:
    """
    Validate Python code for potential security issues.

    This function checks the code for disallowed operations, imports, and other
    security concerns before execution. Security restrictions can be configured
    in the config.yml file under the code_execution section.

    Args:
        code: Python code to validate

    Raises:
        ValueError: If the code contains disallowed operations or imports
    """
    if len(code) > MAX_CODE_SIZE:
        raise ValueError(f"Code exceeds maximum size of {MAX_CODE_SIZE} characters")

    # Check configuration for security settings
    allow_dangerous_ops = False
    additional_imports = []
    try:
        # Attempt to load configuration
        import os
        import yaml
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(project_root, 'config.yml')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                # Check if dangerous operations are allowed
                if config and 'code_execution' in config:
                    code_exec_config = config['code_execution']
                    if 'allow_dangerous_operations' in code_exec_config:
                        allow_dangerous_ops = code_exec_config['allow_dangerous_operations']
                    # Check for additional allowed imports
                    if 'allowed_operations' in code_exec_config and 'imports' in code_exec_config['allowed_operations']:
                        additional_imports = code_exec_config['allowed_operations']['imports']
    except Exception as e:
        logger.warning(f"Failed to load configuration for code validation: {str(e)}")
        # If there's an error, default to safe behavior
        allow_dangerous_ops = False

    # Define allowed imports (expanded for utility while remaining safe)
    allowed_imports: Set[str] = {
        'math', 'random', 'string', 're', 'collections', 'itertools',
        'json', 'datetime', 'statistics', 'functools', 'operator',
        'numpy', 'pandas'  # Added for basic data processing
    }
    
    # Add additional imports from configuration
    for import_name in additional_imports:
        allowed_imports.add(import_name)

    # Check for any import statements
    import_matches = re.finditer(r'(?:from\s+(\w+)|import\s+(\w+))', code)
    for match in import_matches:
        module = match.group(1) or match.group(2)
        if module and module not in allowed_imports:
            raise ValueError(f"Import of '{module}' is not allowed")

    # If dangerous operations are allowed, skip the rest of validation
    if allow_dangerous_ops:
        logger.warning("Dangerous operations allowed by configuration. Security restrictions disabled.")
        return

    # Otherwise, check for dangerous operations
    dangerous_operations = [
        r'exec\s*\(',       # Code execution
        r'eval\s*\(',       # Code evaluation
        r'os\.',            # OS module access
        r'sys\.',           # Sys module access
        r'subprocess\.',    # Subprocess access
        r'shutil\.',        # Shutil access
        r'__import__\s*\(',
        r'open\s*\(',       # File operations
        r'globals\s*\(',    # Access to globals
        r'locals\s*\(',     # Access to locals
        r'compile\s*\(',    # Code compilation
        r'builtins\.',      # Access to builtins
    ]

    for pattern in dangerous_operations:
        if re.search(pattern, code):
            raise ValueError(f"Disallowed operation detected: {pattern}")


def execute_python_code(
    code: str,
    timeout: int = DEFAULT_TIMEOUT,
    setup_code: Optional[str] = None
) -> str:
    """
    Execute Python code using the system Python interpreter in a controlled environment.

    This function validates, sets up, and executes Python code safely, with timeout
    protection and security checks.

    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds (default: 10, max: 60)
        setup_code: Optional setup code to run before the main code

    Returns:
        String containing the output of the code execution

    Raises:
        CodeExecutionError: If there's an error during execution
    """
    # Start loading indicator
    print("Generating code...", end="", flush=True)

    # Validate inputs
    if not isinstance(code, str) or not code.strip():
        print("\rGenerated!          \n", flush=True)
        return "Error: Code must be a non-empty string"

    if not isinstance(timeout, int) or timeout <= 0:
        print("\rGenerated!          \n", flush=True)
        return "Error: Timeout must be a positive integer"

    # Cap timeout to maximum allowed value
    timeout = min(timeout, MAX_TIMEOUT)

    # Validate code for security issues
    try:
        validate_code(code)
    except ValueError as e:
        print("\rGenerated!          \n", flush=True)
        return f"Code validation error: {str(e)}"

    # Check syntax before execution
    try:
        ast.parse(code)
    except SyntaxError as e:
        print("\rGenerated!          \n", flush=True)
        return f"Syntax error in code: {str(e)}"

    # Temporary file paths
    temp_file_path = None
    setup_file_path = None

    try:
        logger.info(f"Executing Python code with timeout {timeout}s")

        # Handle setup code if provided
        if setup_code:
            try:
                validate_code(setup_code)
                ast.parse(setup_code)
                with tempfile.NamedTemporaryFile(suffix='_setup.py', mode='w', delete=False) as setup_file:
                    setup_file_path = setup_file.name
                    setup_file.write(setup_code)
                subprocess.run(
                    [sys.executable, setup_file_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
            except ValueError as e:
                return f"Setup code validation error: {str(e)}"
            except SyntaxError as e:
                return f"Syntax error in setup code: {str(e)}"

        # Create temporary file for main code
        with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as temp_file:
            temp_file_path = temp_file.name
            # Add safe imports and user code
            imports = [
                "import math",
                "import random",
                "import string",
                "import re",
                "from collections import Counter, defaultdict",
                "import json",
                "import datetime",
                "try:",
                "    import numpy as np",
                "except ImportError:",
                "    pass",
                "try:",
                "    import pandas as pd",
                "except ImportError:",
                "    pass",
                "",
                "# User code starts here",
                code
            ]
            temp_file.write("\n".join(imports))

        # Execute the code
        result = subprocess.run(
            [sys.executable, temp_file_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        # Prepare detailed output
        output_parts: List[str] = []
        if result.stdout:
            output_parts.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output_parts.append(f"STDERR:\n{result.stderr}")
        if result.returncode != 0:
            output_parts.append(f"Exit code: {result.returncode}")
            traceback_lines = result.stderr.splitlines()
            if traceback_lines:
                output_parts.append("Traceback (most recent call last):")
                output_parts.extend(traceback_lines)

        return "\n".join(output_parts) if output_parts else "Code executed successfully with no output."
    except subprocess.TimeoutExpired:
        logger.warning(f"Code execution timed out after {timeout} seconds")
        return f"Code execution timed out after {timeout} seconds"
    except Exception as e:
        logger.error(f"Error executing Python code: {str(e)}")
        return f"Error executing Python code: {str(e)}\n{traceback.format_exc()}"
    finally:
        print("\rGenerated!          \n", flush=True)  # Clear loading line and show completion
        # Clean up temporary files
        for file_path in [temp_file_path, setup_file_path]:
            if file_path and os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                    logger.debug(f"Temporary file {file_path} removed")
                except Exception as e:
                    logger.error(f"Failed to remove temporary file {file_path}: {str(e)}")


# Define the anon_coder tool
anon_coder_tool = Tool(
    name="anon_coder",
    description="""Generate and execute Python code based on natural language requests or direct input.
    The code must be safe, handle errors gracefully, and provide clear output.
    Examples:
    - "Calculate the factorial of 5" -> Generates and executes code to compute factorial
    - "Create a list of squares from 1 to 10" -> Generates code to produce the list
    - Direct code: "print('Hello, World!')" -> Executes the provided code safely

    Features:
    - Executes code with timeout protection (default: 10s, max: 60s).
    - Restricts imports to safe modules (e.g., math, random, numpy).
    - Blocks dangerous operations (e.g., file access, exec).
    - Returns detailed output including stdout, stderr, and errors.""",
    parameters={
        "code": ParamType.STRING,
        "timeout": ParamType.INTEGER,
        "setup_code": ParamType.STRING
    },
    func=execute_python_code
)


def get_tool() -> Tool:
    """
    Return the anon_coder tool instance for tinyAgent integration.

    Returns:
        Tool: The anon_coder tool object
    """
    return anon_coder_tool
