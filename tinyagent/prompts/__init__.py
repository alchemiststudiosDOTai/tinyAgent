"""tinyagent.prompts package exports."""

from .loader import get_prompt_fallback
from .templates import BAD_JSON, CODE_SYSTEM, SYSTEM

__all__ = [
    "SYSTEM",
    "BAD_JSON",
    "CODE_SYSTEM",
    "get_prompt_fallback",
]
