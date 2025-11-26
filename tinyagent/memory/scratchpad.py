"""
tinyagent.memory.scratchpad
Working memory that persists across agent steps.

Public surface
--------------
AgentMemory  – dataclass
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["AgentMemory"]


@dataclass
class AgentMemory:
    """
    Working memory that maintains state across agent steps.

    This class provides a structured way for the agent to:
    - Store computed values for later use
    - Record observations and learnings
    - Track failed approaches to avoid repeating mistakes

    Parameters
    ----------
    variables : dict[str, Any]
        Computed values that persist across steps
    observations : list[str]
        What the agent has learned during execution
    failed_approaches : list[str]
        Approaches that didn't work (to avoid repetition)

    Examples
    --------
    >>> memory = AgentMemory()
    >>> memory.store("result", 42)
    >>> memory.observe("The API returns JSON, not plain text")
    >>> memory.fail("Tried parsing as XML - wrong format")
    >>> memory.to_context()
    '## Working Memory\\n\\n### Variables\\n- result: 42\\n...'
    """

    variables: dict[str, Any] = field(default_factory=dict)
    observations: list[str] = field(default_factory=list)
    failed_approaches: list[str] = field(default_factory=list)

    def store(self, name: str, value: Any) -> None:
        """
        Store a computed value in working memory.

        Parameters
        ----------
        name : str
            Variable name to store under
        value : Any
            Value to store
        """
        self.variables[name] = value

    def recall(self, name: str, default: Any = None) -> Any:
        """
        Recall a stored value from working memory.

        Parameters
        ----------
        name : str
            Variable name to recall
        default : Any
            Default value if not found

        Returns
        -------
        Any
            The stored value or default
        """
        return self.variables.get(name, default)

    def observe(self, observation: str) -> None:
        """
        Record an observation about the task.

        Parameters
        ----------
        observation : str
            What was learned or noticed
        """
        self.observations.append(observation)

    def fail(self, approach: str) -> None:
        """
        Record a failed approach.

        Parameters
        ----------
        approach : str
            Description of what didn't work
        """
        self.failed_approaches.append(approach)

    def clear(self) -> None:
        """Clear all memory state."""
        self.variables.clear()
        self.observations.clear()
        self.failed_approaches.clear()

    def to_context(self) -> str:
        """
        Convert memory to a context string for the LLM.

        Returns
        -------
        str
            Formatted context string with all memory contents
        """
        parts = ["## Working Memory"]

        if self.variables:
            parts.append("\n### Stored Values")
            for name, value in self.variables.items():
                value_repr = repr(value)
                if len(value_repr) > 100:
                    value_repr = value_repr[:100] + "..."
                parts.append(f"- {name}: {value_repr}")

        if self.observations:
            parts.append("\n### Observations")
            for obs in self.observations:
                parts.append(f"- {obs}")

        if self.failed_approaches:
            parts.append("\n### Failed Approaches (avoid these)")
            for approach in self.failed_approaches:
                parts.append(f"- {approach}")

        if len(parts) == 1:
            return ""  # Empty memory

        return "\n".join(parts)

    def to_namespace(self) -> dict[str, Any]:
        """
        Export memory for injection into execution namespace.

        Returns
        -------
        dict[str, Any]
            Dictionary of variables for namespace injection
        """
        return {
            "memory": self,
            "store": self.store,
            "recall": self.recall,
            "observe": self.observe,
            **self.variables,
        }
