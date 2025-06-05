"""
Chat functionality for the tinyAgent framework.

This package provides chat-related functionality for the tinyAgent framework,
including direct conversation with the language model without using tools.
"""

from .chat_mode import run_chat_mode

__all__ = [
    "run_chat_mode",
]
