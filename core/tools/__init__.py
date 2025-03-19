"""
Tools for the tinyAgent framework.

This package provides built-in tools and utilities for loading external tools.
It includes both Python-based tools and support for external tools written in
other languages like Go, Bash, etc.
"""

from .external import load_external_tools
from .anon_coder import anon_coder_tool
from .llm_serializer import llm_serializer_tool
from .ripgrep import ripgrep_tool
from .brave_search import brave_web_search_tool
from .aider import aider_tool

__all__ = [
    # Tool loading utilities
    'load_external_tools',
    
    # Built-in tools
    'anon_coder_tool',
    'llm_serializer_tool',
    'ripgrep_tool',
    'brave_web_search_tool',
    'aider_tool',
]
