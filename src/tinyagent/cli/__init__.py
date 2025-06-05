"""
Command-line interface for the tinyAgent framework.

This package provides the CLI components for the tinyAgent framework,
including command parsing, interactive mode, and specific command handlers.
"""

from .colors import Colors
from .main import main
from .spinner import Spinner

__all__ = [
    "main",
    "Spinner",
    "Colors",
]
