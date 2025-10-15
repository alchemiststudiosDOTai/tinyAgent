"""tinyagent.tools package exports."""

from .builtin import web_search
from .validation import ToolValidationError, validate_tool_class

__all__ = [
    "web_search",
    "validate_tool_class",
    "ToolValidationError",
]
