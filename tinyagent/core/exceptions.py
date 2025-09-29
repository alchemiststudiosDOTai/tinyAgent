"""
tinyagent.exceptions
Custom exception classes for agent execution and final answer handling.

Public surface
--------------
StepLimitReached      – exception
MultipleFinalAnswers  – exception
InvalidFinalAnswer    – exception
"""

from __future__ import annotations

from typing import Any

__all__ = ["StepLimitReached", "MultipleFinalAnswers", "InvalidFinalAnswer"]


class StepLimitReached(RuntimeError):
    """
    Raised when no answer is produced within the maximum number of steps.

    This exception is raised by both ReactAgent and TinyCodeAgent when they
    exceed their step limit without producing a final answer, even after
    attempting a final answer attempt.

    Parameters
    ----------
    message : str
        Error message describing the failure
    steps_taken : int, optional
        Number of steps taken before hitting the limit
    final_attempt_made : bool, optional
        Whether a final attempt was made before giving up
    context : dict[str, Any], optional
        Additional context about the execution state
    """

    def __init__(
        self,
        message: str = "Exceeded max steps without an answer.",
        *,
        steps_taken: int | None = None,
        final_attempt_made: bool = False,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.steps_taken = steps_taken
        self.final_attempt_made = final_attempt_made
        self.context = context or {}


class MultipleFinalAnswers(RuntimeError):
    """
    Raised when an agent attempts to set multiple final answers.

    This exception enforces the constraint that each agent execution
    can only produce one final answer. It's raised by the Finalizer
    when set() is called more than once.

    Parameters
    ----------
    message : str
        Error message describing the violation
    first_answer : Any, optional
        The first final answer that was set
    attempted_answer : Any, optional
        The answer that was attempted to be set as a duplicate
    """

    def __init__(
        self,
        message: str = "Multiple final answers attempted.",
        *,
        first_answer: Any = None,
        attempted_answer: Any = None,
    ):
        super().__init__(message)
        self.first_answer = first_answer
        self.attempted_answer = attempted_answer


class InvalidFinalAnswer(ValueError):
    """
    Raised when a final answer fails validation.

    This exception is raised when a final answer doesn't meet the expected
    format or validation criteria (e.g., malformed JSON, missing required fields).

    Parameters
    ----------
    message : str
        Error message describing the validation failure
    raw_content : str, optional
        The raw content that failed validation
    validation_error : Exception, optional
        The underlying validation error, if any
    """

    def __init__(
        self,
        message: str = "Final answer failed validation.",
        *,
        raw_content: str | None = None,
        validation_error: Exception | None = None,
    ):
        super().__init__(message)
        self.raw_content = raw_content
        self.validation_error = validation_error
