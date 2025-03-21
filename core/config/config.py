"""
Configuration management for the tinyAgent framework.

This module provides functions for loading, validating, and accessing configuration
settings from different sources (files, environment variables, etc.).
"""

import os
import yaml
from typing import Dict, Any, Optional, TypedDict, Union, cast
from dataclasses import dataclass, field

from ..exceptions import ConfigurationError
from ..logging import get_logger

# Set up logger
logger = get_logger(__name__)


class ParsingConfig(TypedDict, total=False):
    """Configuration for response parsing."""
    strict_json: bool
    fallback_parsers: Dict[str, bool]


class ModelConfig(TypedDict, total=False):
    """Configuration for models."""
    default: str


class RetriesConfig(TypedDict, total=False):
    """Configuration for retry behavior."""
    max_attempts: int


class RateLimitConfig(TypedDict, total=False):
    """Configuration for rate limiting."""
    global_limit: int
    tool_limits: Dict[str, int]


class LoggingConfig(TypedDict, total=False):
    """Configuration for logging."""
    level: str
    file: Optional[str]


class TinyAgentConfig(TypedDict, total=False):
    """Top-level configuration structure."""
    parsing: ParsingConfig
    model: ModelConfig
    retries: RetriesConfig
    rate_limits: RateLimitConfig
    logging: LoggingConfig


# Default configuration
DEFAULT_CONFIG: TinyAgentConfig = {
    "parsing": {
        "strict_json": False,
        "fallback_parsers": {
            "template": True,
            "regex": True
        }
    },
    "model": {
        "default": "qwen/qwq-32B"
    },
    "retries": {
        "max_attempts": 3
    },
    "rate_limits": {
        "global_limit": 30,
        "tool_limits": {}
    },
    "logging": {
        "level": "INFO",
        "file": None
    }
}


def load_config(config_path: Optional[str] = None) -> TinyAgentConfig:
    """
    Load configuration from YAML file, with fallback to default values.
    
    This function attempts to load configuration from a YAML file. If the file
    doesn't exist or there's an error loading it, it falls back to default values.
    
    Args:
        config_path: Path to config.yml file. If None, uses config.yml from project root.
        
    Returns:
        Dict containing configuration values
        
    Raises:
        ConfigurationError: If there's an error with the configuration format
    """
    # Always use project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    if config_path is None:
        config_path = os.path.join(project_root, 'config.yml')
    elif not os.path.isabs(config_path):
        # If relative path provided, make it relative to project root
        config_path = os.path.join(project_root, config_path)
    
    config = cast(TinyAgentConfig, DEFAULT_CONFIG.copy())
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as file:
                yaml_config = yaml.safe_load(file)
                
                if yaml_config:
                    # Validate the config
                    if not isinstance(yaml_config, dict):
                        raise ConfigurationError("Configuration must be a dictionary")
                    
                    # Update config with values from YAML
                    _update_nested_dict(config, yaml_config)
                    logger.info(f"Configuration loaded from {config_path}")
                else:
                    logger.warning(f"Empty configuration file: {config_path}")
        else:
            logger.info(f"Configuration file not found at {config_path}, using defaults")
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration: {str(e)}")
        raise ConfigurationError(f"Invalid YAML in configuration file: {e}")
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        logger.info("Using default configuration")
    
    return config


def _update_nested_dict(base_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> None:
    """
    Update a nested dictionary with values from another dictionary.
    
    This function recursively updates a nested dictionary with values from another
    dictionary, preserving the structure of the base dictionary.
    
    Args:
        base_dict: The dictionary to update
        update_dict: The dictionary with new values
    """
    for key, value in update_dict.items():
        if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
            _update_nested_dict(base_dict[key], value)
        else:
            base_dict[key] = value


def get_config_value(config: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Get a value from the config using a dot-notation path.
    
    This function retrieves a value from a nested dictionary using a dot-notation
    path. If the key doesn't exist, it returns the default value.
    
    Args:
        config: The configuration dictionary
        key_path: Dot-notation path to the desired value (e.g., 'parsing.strict_json')
        default: Value to return if the key is not found
        
    Returns:
        The configuration value or default if not found
        
    Examples:
        >>> config = {"parsing": {"strict_json": True}}
        >>> get_config_value(config, "parsing.strict_json")
        True
        >>> get_config_value(config, "parsing.unknown", False)
        False
    """
    keys = key_path.split('.')
    current = config
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current


def validate_config(config: TinyAgentConfig) -> None:
    """
    Validate the configuration to ensure it matches the expected format.
    
    Args:
        config: The configuration to validate
        
    Raises:
        ConfigurationError: If the configuration is invalid
    """
    # Validate model.default
    if "model" in config and "default" in config["model"]:
        if not isinstance(config["model"]["default"], str):
            raise ConfigurationError("model.default must be a string")
    
    # Validate retries.max_attempts
    if "retries" in config and "max_attempts" in config["retries"]:
        if not isinstance(config["retries"]["max_attempts"], int):
            raise ConfigurationError("retries.max_attempts must be an integer")
        if config["retries"]["max_attempts"] < 1:
            raise ConfigurationError("retries.max_attempts must be at least 1")
    
    # Validate parsing.strict_json
    if "parsing" in config and "strict_json" in config["parsing"]:
        if not isinstance(config["parsing"]["strict_json"], bool):
            raise ConfigurationError("parsing.strict_json must be a boolean")
    
    # Validate rate_limits.global_limit
    if "rate_limits" in config and "global_limit" in config["rate_limits"]:
        if not isinstance(config["rate_limits"]["global_limit"], int):
            raise ConfigurationError("rate_limits.global_limit must be an integer")
