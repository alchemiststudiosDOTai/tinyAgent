"""
tinyagent.types
Core data types for final answer handling and agent execution results.

Public surface
--------------
FinalAnswer  – dataclass
RunResult    – dataclass
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Literal

__all__ = ["FinalAnswer", "RunResult"]


@dataclass(frozen=True)
class FinalAnswer:
    """
    Represents a final answer from an agent with metadata.

    This class encapsulates the final answer value along with metadata
    about how it was obtained (e.g., through normal execution or final attempt).

    Parameters
    ----------
    value : Any
        The actual answer value (string, dict, or any other type)
    source : Literal["normal", "final_attempt"]
        How the answer was obtained
    timestamp : float
        Unix timestamp when the answer was created
    metadata : dict[str, Any]
        Additional metadata about the answer
    """

    value: Any
    source: Literal["normal", "final_attempt"] = "normal"
    timestamp: float = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        """Set default values for mutable fields."""
        if self.timestamp is None:
            object.__setattr__(self, "timestamp", time.time())
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


@dataclass(frozen=True)
class RunResult:
    """
    Complete result of an agent execution with state tracking.

    This class provides a structured way to return not just the final answer,
    but also execution metadata like step count, timing, and final state.

    Parameters
    ----------
    output : str
        The final output/answer from the agent
    final_answer : FinalAnswer | None
        Structured final answer with metadata, if available
    state : Literal["completed", "step_limit_reached", "error"]
        Final execution state
    steps_taken : int
        Number of reasoning/execution steps taken
    duration_seconds : float
        Total execution time in seconds
    error : Exception | None
        Exception that caused termination, if any
    metadata : dict[str, Any]
        Additional execution metadata
    """

    output: str
    final_answer: FinalAnswer | None = None
    state: Literal["completed", "step_limit_reached", "error"] = "completed"
    steps_taken: int = 0
    duration_seconds: float = 0.0
    error: Exception | None = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        """Set default values for mutable fields."""
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})
