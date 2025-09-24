"""
tinyagent.finalizer
Singleton finalizer for managing final answers with idempotent operations.

Public surface
--------------
Finalizer  – class
"""

from __future__ import annotations

import threading
from typing import Any, Literal

from .exceptions import MultipleFinalAnswers
from .types import FinalAnswer

__all__ = ["Finalizer"]


class Finalizer:
    """
    Thread-safe singleton for managing final answers with idempotent operations.

    The Finalizer ensures that only one final answer can be set per agent execution,
    providing a clean contract for final answer handling across different agent types.

    Key properties:
    - Thread-safe operations using locks
    - Idempotent set() operation (raises on duplicate calls)
    - Immutable after first set() call
    - Clean get()/is_set() interface for checking state

    Examples
    --------
    >>> finalizer = Finalizer()
    >>> finalizer.is_set()
    False
    >>> finalizer.set("My answer", source="normal")
    >>> finalizer.is_set()
    True
    >>> finalizer.get().value
    'My answer'
    >>> finalizer.set("Another answer")  # Raises MultipleFinalAnswers
    """

    def __init__(self):
        """Initialize a new Finalizer instance."""
        self._final_answer: FinalAnswer | None = None
        self._lock = threading.Lock()

    def set(
        self,
        value: Any,
        *,
        source: Literal["normal", "final_attempt"] = "normal",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Set the final answer (idempotent - raises on second call).

        Parameters
        ----------
        value : Any
            The final answer value
        source : str, optional
            How the answer was obtained ("normal" or "final_attempt")
        metadata : dict[str, Any], optional
            Additional metadata about the answer

        Raises
        ------
        MultipleFinalAnswers
            If set() has already been called successfully
        """
        with self._lock:
            if self._final_answer is not None:
                raise MultipleFinalAnswers(
                    "Final answer already set. Each execution can only have one final answer.",
                    first_answer=self._final_answer.value,
                    attempted_answer=value,
                )

            self._final_answer = FinalAnswer(
                value=value,
                source=source,
                metadata=metadata or {},
            )

    def get(self) -> FinalAnswer | None:
        """
        Get the final answer if set, otherwise None.

        Returns
        -------
        FinalAnswer | None
            The final answer with metadata, or None if not set
        """
        with self._lock:
            return self._final_answer

    def is_set(self) -> bool:
        """
        Check if a final answer has been set.

        Returns
        -------
        bool
            True if a final answer has been set, False otherwise
        """
        with self._lock:
            return self._final_answer is not None

    def reset(self) -> None:
        """
        Reset the finalizer to allow setting a new final answer.

        This method is primarily intended for testing and should be used
        with caution in production code.
        """
        with self._lock:
            self._final_answer = None
