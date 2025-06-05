"""
Logging helper utilities for tinyAgent.

This module provides reusable structured logging functions with reasoning support,
originally from the orchestrator module.
"""

import json
import time
from typing import Any, Dict, Optional

from ..logging import get_logger

logger = get_logger(__name__)


def log_task_event(
    task_id: str,
    event: str,
    details: Optional[Dict[str, Any]] = None,
    level: str = "info",
    reasoning: Optional[str] = None,
) -> None:
    """Helper function for structured task logging with reasoning."""
    log_data = {
        "task_id": task_id,
        "event": event,
        "timestamp": time.time(),
        "details": details or {},
        "reasoning": reasoning,
    }
    msg = f"Task Event: {json.dumps(log_data)}"
    if level == "info":
        logger.info(msg)
    elif level == "error":
        logger.error(msg)
    elif level == "debug":
        logger.debug(msg)


def log_decision(
    task_id: str,
    decision: str,
    context: Dict[str, Any],
    reasoning: str,
) -> None:
    """Helper function for logging decisions with context and reasoning."""
    log_data = {
        "task_id": task_id,
        "decision": decision,
        "context": context,
        "reasoning": reasoning,
        "timestamp": time.time(),
    }
    logger.info(f"Decision Log: {json.dumps(log_data)}")


def log_section_header(title: str) -> None:
    """Helper function for logging section headers with visual separators."""
    separator = "=" * 50
    logger.info(f"\n{separator}")
    logger.info(f"{title}")
    logger.info(f"{separator}\n")


def log_step(
    step_number: int,
    title: str,
    details: Dict[str, Any],
    reasoning: str,
) -> None:
    """Helper function for logging steps with clear formatting."""
    logger.info(f"\nStep {step_number}: {title}")
    logger.info("-" * 30)
    logger.info(f"Reasoning: {reasoning}")
    for key, value in details.items():
        logger.info(f"{key}: {value}")
    logger.info("-" * 30)
