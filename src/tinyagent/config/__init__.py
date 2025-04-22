"""
Configuration management for the tinyAgent framework.

This package provides utilities for loading, validating, and accessing
configuration settings from different sources (files, environment variables, etc.).
"""

from .config import load_config, get_config_value, TinyAgentConfig

__all__ = [
    'load_config',
    'get_config_value',
    'TinyAgentConfig',
]
