"""
External tools support for the tinyAgent framework.

This module provides utilities for loading and executing tools implemented in
languages other than Python, such as Go, Bash, etc. It handles the JSON-based
communication protocol and manages the execution of external processes.
"""

import os
import json
import subprocess
from typing import Dict, Any, List, Optional, Callable, cast

from ..logging import get_logger
from ..tool import Tool, ParamType
from ..exceptions import ToolError

# Set up logger
logger = get_logger(__name__)


def load_external_tools(tools_dir: str = "external_tools") -> List[Tool]:
    """
    Load external tools from manifest.json files in subdirectories.
    
    This function searches for manifest.json files in tool subdirectories
    and creates Tool instances for each one. The manifest must contain
    name, description, parameters, and executable fields.
    
    Args:
        tools_dir: Directory containing tool subdirectories
        
    Returns:
        List of Tool instances loaded from manifests
        
    Examples:
        >>> tools = load_external_tools("./custom_tools")
        >>> len(tools)
        2
        >>> tools[0].name
        'go_calculator'
    """
    tools: List[Tool] = []
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Get absolute path to tools directory
    if not os.path.isabs(tools_dir):
        tools_dir = os.path.join(base_dir, tools_dir)
    
    logger.info(f"Looking for external tools in {tools_dir}")
    
    # Process each subdirectory
    try:
        for item in os.listdir(tools_dir):
            path = os.path.join(tools_dir, item)
            manifest_path = os.path.join(path, "manifest.json")
            
            if os.path.isdir(path) and os.path.exists(manifest_path):
                try:
                    # Load manifest
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                    
                    # Validate mandatory fields
                    required_fields = ["name", "description", "parameters", "executable"]
                    if not all(k in manifest for k in required_fields):
                        missing = [k for k in required_fields if k not in manifest]
                        logger.error(f"Missing required fields in manifest: {', '.join(missing)}")
                        continue
                    
                    # Create parameter types dictionary with defaults
                    params: Dict[str, ParamType] = {}
                    param_defaults: Dict[str, Any] = {}
                    for param_name, param_info in manifest.get("parameters", {}).items():
                        # Handle both old and new parameter format
                        if isinstance(param_info, str):
                            # Old format: "param_name": "type"
                            param_type_str = param_info
                            required = True
                            default = None
                        else:
                            # New format: "param_name": {"type": "type", "required": bool, "default": value}
                            param_type_str = param_info.get("type", "any")
                            required = param_info.get("required", True)
                            default = param_info.get("default")
                            
                        # Set parameter type
                        if param_type_str == "string":
                            params[param_name] = ParamType.STRING
                        elif param_type_str == "number" or param_type_str == "float":
                            params[param_name] = ParamType.FLOAT
                        elif param_type_str == "integer":
                            params[param_name] = ParamType.INTEGER
                        else:
                            params[param_name] = ParamType.ANY
                            
                        # Store default if provided
                        if not required and default is not None:
                            param_defaults[param_name] = default
                    
                    # Create the tool executor function with defaults
                    tool_executor = create_external_executor(path, manifest, param_defaults)
                    
                    # Create the tool with the executor and manifest
                    tool = Tool(
                        name=manifest["name"],
                        description=manifest["description"],
                        parameters=params,
                        func=tool_executor,
                        manifest=manifest  # Store the full manifest for parameter handling
                    )
                    
                    # Add rate limit if specified in manifest
                    if "rate_limit" in manifest:
                        try:
                            tool.rate_limit = int(manifest["rate_limit"])
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid rate_limit in manifest for {manifest['name']}")
                    
                    tools.append(tool)
                    logger.info(f"Loaded external tool: {manifest['name']}")
                    
                except Exception as e:
                    logger.error(f"Error loading external tool from {path}: {str(e)}")
    except Exception as e:
        logger.error(f"Error scanning for external tools: {str(e)}")
    
    return tools


def create_external_executor(tool_path: str, manifest: Dict[str, Any], param_defaults: Dict[str, Any]) -> Callable[..., Any]:
    """
    Create a function that executes an external tool.
    
    This function creates a closure that captures the path and manifest
    information for an external tool, and returns a function that will
    execute the tool with the given arguments.
    
    Args:
        tool_path: Path to the directory containing the tool
        manifest: Tool manifest data
        
    Returns:
        Function that executes the external tool
    """
    def execute_external_tool(**kwargs: Any) -> Any:
        """
        Execute an external tool with the given arguments.
        
        Args:
            **kwargs: Keyword arguments to pass to the tool
            
        Returns:
            Tool execution result
            
        Raises:
            ToolError: If the tool fails to execute
        """
        # Build the path to the executable
        executable = os.path.join(tool_path, manifest["executable"])
        
        # Ensure it's executable
        if not os.access(executable, os.X_OK):
            try:
                os.chmod(executable, os.stat(executable).st_mode | 0o111)
                logger.debug(f"Made {executable} executable")
            except Exception as e:
                raise ToolError(f"Could not make {executable} executable: {str(e)}")
        
        # Apply defaults to kwargs
        input_kwargs = param_defaults.copy()
        input_kwargs.update(kwargs)
        
        # Execute the tool with JSON input
        input_data = json.dumps(input_kwargs)
        try:
            logger.debug(f"Executing external tool: {executable}")
            
            result = subprocess.run(
                [executable],
                input=input_data,
                capture_output=True,
                text=True,
                check=False,  # Don't raise on non-zero exit
                encoding='utf-8'
            )
            
            logger.debug(f"External tool exit code: {result.returncode}")
            
            # Try to parse JSON output
            if result.stdout:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    # If output isn't valid JSON, return as plain text
                    return {"output": result.stdout.strip(), "error": None}
            elif result.stderr:
                # Return error if no stdout but stderr is present
                error_msg = result.stderr.strip()
                logger.error(f"External tool error: {error_msg}")
                return {"error": error_msg, "output": None}
            else:
                # Return error if no output at all
                error_msg = f"Tool returned exit code {result.returncode} with no output"
                logger.error(error_msg)
                return {"error": error_msg, "output": None}
                
        except subprocess.TimeoutExpired:
            error_msg = "External tool execution timed out"
            logger.error(error_msg)
            return {"error": error_msg, "output": None}
        except Exception as e:
            error_msg = f"Failed to execute external tool: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "output": None}
            
    return execute_external_tool


def validate_external_tool_manifest(manifest: Dict[str, Any]) -> List[str]:
    """
    Validate an external tool manifest file.
    
    Args:
        manifest: Tool manifest data
        
    Returns:
        List of validation errors, empty if valid
    """
    errors: List[str] = []
    
    # Check required fields
    required_fields = ["name", "description", "parameters", "executable"]
    for field in required_fields:
        if field not in manifest:
            errors.append(f"Missing required field: {field}")
    
    # Check name format
    if "name" in manifest:
        name = manifest["name"]
        if not isinstance(name, str):
            errors.append("Tool name must be a string")
        elif not name.islower() or " " in name:
            errors.append("Tool name must be lowercase with no spaces")
    
    # Check description
    if "description" in manifest:
        desc = manifest["description"]
        if not isinstance(desc, str):
            errors.append("Tool description must be a string")
        elif len(desc) < 10:
            errors.append("Tool description must be at least 10 characters")
    
    # Check parameters
    if "parameters" in manifest:
        params = manifest["parameters"]
        if not isinstance(params, dict):
            errors.append("Tool parameters must be an object")
        else:
            for param_name, param_info in params.items():
                if not isinstance(param_name, str):
                    errors.append(f"Parameter name must be a string: {param_name}")
                
                # Handle both old and new parameter formats
                if isinstance(param_info, str):
                    param_type = param_info
                    valid_types = ["string", "integer", "float", "number", "any"]
                    if param_type not in valid_types:
                        errors.append(
                            f"Invalid parameter type '{param_type}' for '{param_name}'. "
                            f"Valid types: {', '.join(valid_types)}"
                        )
                elif isinstance(param_info, dict):
                    if "type" not in param_info:
                        errors.append(f"Parameter '{param_name}' missing required 'type' field")
                    else:
                        param_type = param_info["type"]
                        valid_types = ["string", "integer", "float", "number", "any"]
                        if param_type not in valid_types:
                            errors.append(
                                f"Invalid parameter type '{param_type}' for '{param_name}'. "
                                f"Valid types: {', '.join(valid_types)}"
                            )
                    
                    # Validate default value type if provided
                    if "default" in param_info:
                        default = param_info["default"]
                        if param_type == "string" and not isinstance(default, str):
                            errors.append(f"Default value for '{param_name}' must be a string")
                        elif param_type == "integer" and not isinstance(default, int):
                            errors.append(f"Default value for '{param_name}' must be an integer")
                        elif param_type in ["float", "number"] and not isinstance(default, (int, float)):
                            errors.append(f"Default value for '{param_name}' must be a number")
                else:
                    errors.append(f"Invalid parameter specification for '{param_name}'")
    
    # Check executable
    if "executable" in manifest:
        executable = manifest["executable"]
        if not isinstance(executable, str):
            errors.append("Executable must be a string")
    
    return errors
