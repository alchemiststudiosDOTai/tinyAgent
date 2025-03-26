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
    BOOLEAN = "boolean"
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

    def validate_args(self, **kwargs):
        """
        Validate the arguments passed to the tool against its parameter specifications.
        
        Args:
            **kwargs: The arguments to validate
            
        Returns:
            bool: True if validation passes
            
        Raises:
            ValueError: If validation fails
        """
        print(f"\nValidating args for tool: {self.name}")
        print(f"Arguments provided: {kwargs}")
        
        # If using manifest-based validation
        if hasattr(self, 'manifest') and self.manifest:
            manifest_params = self.manifest.get('parameters', {})
            required_params = self.manifest.get('required', [])
            
            # Check required parameters
            for param in required_params:
                if param not in kwargs:
                    raise ValueError(f"Missing required parameter: {param}")
            
            # Validate parameter types and values
            for param_name, param_value in kwargs.items():
                if param_name not in manifest_params:
                    if not self.manifest.get('additionalProperties', True):
                        raise ValueError(f"Unknown parameter: {param_name}")
                    continue
                    
                param_spec = manifest_params[param_name]
                
                # Skip validation for None values on optional parameters
                if param_value is None and not param_spec.get('required', False):
                    continue
                    
                # Validate enum values if specified
                if 'enum' in param_spec and param_value is not None:
                    if param_value not in param_spec['enum']:
                        raise ValueError(f"Invalid value for {param_name}. Must be one of: {param_spec['enum']}")
                
                # Validate type if specified
                if 'type' in param_spec:
                    expected_type = param_spec['type']
                    if expected_type == 'string' and not isinstance(param_value, str):
                        raise ValueError(f"Parameter {param_name} must be a string")
                    elif expected_type == 'boolean' and not isinstance(param_value, bool):
                        raise ValueError(f"Parameter {param_name} must be a boolean")
                    elif expected_type == 'integer' and not isinstance(param_value, int):
                        raise ValueError(f"Parameter {param_name} must be an integer")
        
        # Legacy parameter validation
        else:
            for param_name, param_type in self.parameters.items():
                if param_name not in kwargs:
                    raise ValueError(f"Missing required parameter: {param_name}")
                
                value = kwargs[param_name]
                if value is None:
                    continue
                    
                if param_type == ParamType.STRING and not isinstance(value, str):
                    raise ValueError(f"Parameter {param_name} must be a string")
                elif param_type == ParamType.INTEGER and not isinstance(value, int):
                    raise ValueError(f"Parameter {param_name} must be an integer")
                elif param_type == ParamType.BOOLEAN and not isinstance(value, bool):
                    raise ValueError(f"Parameter {param_name} must be a boolean")
        
        return True

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
        
        # Validate arguments
        self.validate_args(**args)
        
        try:
            # Execute the function with the original arguments
            result = self.func(**args)
            
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
