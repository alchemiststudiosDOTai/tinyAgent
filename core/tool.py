"""
Tool implementations for the tinyAgent framework.

This module provides the Tool class, which represents a callable function
with metadata that can be executed by the Agent. It also defines parameter
types and validation logic.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Callable, List, Optional, TypeVar, Union, overload
from time import time

from .exceptions import RateLimitExceeded, ToolError


class ParamType(str, Enum):
    """
    Enum for parameter types with string values for backward compatibility.
    
    These types are used to specify what type of data a tool parameter accepts,
    which helps with validation and conversion of input values.
    """
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    ANY = "any"
    
    def __str__(self) -> str:
        """Return the string value of the enum."""
        return self.value


@dataclass
class Tool:
    """
    A callable tool with name, description, parameter definitions, and rate limiting.
    
    This class represents a function that can be called by an Agent. It includes
    metadata about the tool (name, description), parameter definitions, and
    optional rate limiting.
    
    Attributes:
        name: Unique identifier for the tool (lowercase, no spaces)
        description: Clear explanation of what the tool does
        parameters: Dictionary mapping parameter names to types
        func: The actual function that implements the tool's functionality
        rate_limit: Optional maximum number of calls allowed per session
        manifest: Optional manifest data for external tools
        _call_history: Internal list tracking timestamps of successful calls
    """
    name: str
    description: str
    parameters: Dict[str, ParamType]  # param_name -> param_type
    func: Callable[..., Any]
    rate_limit: Optional[int] = None  # Number of calls allowed per session
    manifest: Optional[Dict[str, Any]] = None  # Manifest data for external tools
    _call_history: List[float] = field(default_factory=list, repr=False)  # Timestamps of calls

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and convert arguments to correct types.
        
        Args:
            args: Dictionary of argument names to values
            
        Returns:
            Dictionary of validated and converted arguments
            
        Raises:
            ValueError: If a required parameter is missing or of the wrong type
        """
        validated = {}
        
        # Handle parameters based on manifest if available
        if self.manifest and 'parameters' in self.manifest:
            manifest_params = self.manifest['parameters']
            for param_name, param_info in manifest_params.items():
                # Handle both old and new parameter formats
                if isinstance(param_info, dict):
                    param_type = param_info.get('type', 'any')
                    required = param_info.get('required', True)
                    default = param_info.get('default')
                else:
                    param_type = param_info
                    required = True
                    default = None
                
                if param_name not in args:
                    if required:
                        raise ValueError(f"Missing required parameter: {param_name}")
                    elif default is not None:
                        args[param_name] = default
                    else:
                        continue
                
                value = args[param_name]
                try:
                    if param_type == "integer" or param_type == ParamType.INTEGER:
                        validated[param_name] = int(value)
                    elif param_type in ["float", "number"] or param_type == ParamType.FLOAT:
                        validated[param_name] = float(value)
                    elif param_type == "string" or param_type == ParamType.STRING:
                        validated[param_name] = str(value)
                    else:
                        validated[param_name] = value
                except (ValueError, TypeError):
                    raise ValueError(f"{param_name} must be of type {param_type}")
        else:
            # Fall back to simple parameter validation
            for param_name, param_type in self.parameters.items():
                if param_name not in args:
                    raise ValueError(f"Missing required parameter: {param_name}")
                
                value = args[param_name]
                try:
                    if param_type == ParamType.INTEGER:
                        validated[param_name] = int(value)
                    elif param_type == ParamType.FLOAT:
                        validated[param_name] = float(value)
                    elif param_type == ParamType.STRING:
                        validated[param_name] = str(value)
                    else:
                        validated[param_name] = value
                except (ValueError, TypeError):
                    raise ValueError(f"{param_name} must be of type {param_type}")
                
        return validated

    def check_rate_limit(self):
        """
        Check if the tool has exceeded its rate limit.
        
        Raises:
            RateLimitExceeded: If the rate limit has been exceeded
        """
        if not self.rate_limit or self.rate_limit < 0:  # -1 indicates no limit
            return

        # Count calls in the current session INCLUDING this one
        # The + 1 accounts for the current call being attempted
        if len(self._call_history) + 1 > self.rate_limit:
            raise RateLimitExceeded(self.name, self.rate_limit)

    def __call__(self, **args) -> Any:
        """
        Execute tool with validation and rate limiting.
        
        Args:
            **args: Keyword arguments matching the tool's parameters
            
        Returns:
            The result of executing the tool function
            
        Raises:
            RateLimitExceeded: If the rate limit has been exceeded
            ValueError: If arguments are invalid
            Exception: Any exception raised by the underlying function
        """
        # Check rate limit first
        self.check_rate_limit()
        
        # Validate and convert arguments
        validated_args = self.validate_args(args)
        
        try:
            # Execute the function
            result = self.func(**validated_args)
            
            # Only record successful calls
            if self.rate_limit:
                self._call_history.append(time())
                
            return result
        except Exception as e:
            # Don't count failed calls against rate limit
            if isinstance(e, (RateLimitExceeded, ValueError)):
                # These are validation errors we want to preserve
                raise
            # Wrap other errors
            raise ToolError(f"Error executing tool '{self.name}': {str(e)}") from e
