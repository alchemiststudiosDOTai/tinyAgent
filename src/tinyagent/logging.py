"""
Centralized logging configuration for the tinyAgent framework.

This module provides a consistent logging interface for all components
of the tinyAgent framework. It configures logging formatters, handlers,
and log levels based on configuration or environment variables.
"""

import logging
import os
import sys
from typing import Any, Dict, Optional, Union


def configure_logging(
    log_level: Optional[str] = None, config: Optional[Dict[str, Any]] = None
):
    """
    Configure the logging system for tinyAgent.

    Args:
        log_level: Optional log level to use. If not provided, will check config and environment.
        config: Optional configuration dictionary.
    """
    # Determine log level from inputs, environment, or default to INFO
    level_name = log_level

    if level_name is None and config is not None:
        # Try to get from config
        if isinstance(config, dict) and "logging" in config:
            level_name = config.get("logging", {}).get("level")

    if level_name is None:
        # Try to get from environment
        level_name = os.environ.get("TINYAGENT_LOG_LEVEL")

    if level_name is None:
        # Default to INFO
        level_name = "INFO"

    # Convert level name to logging level
    try:
        level = getattr(logging, level_name.upper())
    except (AttributeError, TypeError):
        level = logging.INFO
        print(f"Invalid log level '{level_name}', defaulting to INFO")

    # Get log format from config or use default
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    if config and "logging" in config and "format" in config["logging"]:
        log_format = config["logging"]["format"]

    # Configure root logger
    logging.basicConfig(
        level=level, format=log_format, handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Apply any additional config-based settings
    if config and "logging" in config:
        logging_config = config.get("logging", {})

        # Configure file logging if specified
        log_file = logging_config.get("file")
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            logging.getLogger().addHandler(file_handler)


def get_logger(name: str, level: Optional[Union[str, int]] = None) -> logging.Logger:
    """
    Get a logger with the given name and optional level.

    Args:
        name: The name of the logger, typically __name__
        level: Optional log level for this specific logger

    Returns:
        A configured logger instance
    """
    logger = logging.getLogger(name)

    # Set level if provided
    if level is not None:
        if isinstance(level, str):
            try:
                numeric_level = getattr(logging, level.upper())
            except (AttributeError, TypeError):
                numeric_level = None

            if numeric_level is not None:
                logger.setLevel(numeric_level)
        else:
            logger.setLevel(level)

    return logger
