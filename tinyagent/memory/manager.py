"""
tinyagent.memory.manager
MemoryManager for storing and pruning conversation steps.

Public surface
--------------
MemoryManager      - Main memory management class
PruneStrategy      - Type alias for pruning functions
keep_last_n_steps  - Keep only last N action steps
prune_old_observations - Truncate old observations
no_pruning         - Identity function (no changes)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, TypeVar

from .steps import ActionStep, Step, SystemPromptStep, TaskStep

__all__ = [
    "MemoryManager",
    "PruneStrategy",
    "keep_last_n_steps",
    "prune_old_observations",
    "no_pruning",
]

# Type alias for pruning strategy functions
PruneStrategy = Callable[[list[Step]], list[Step]]

T = TypeVar("T", bound=Step)


@dataclass
class MemoryManager:
    """
    Manages conversation steps with support for pruning strategies.

    Parameters
    ----------
    steps : list[Step]
        List of conversation steps

    Examples
    --------
    >>> manager = MemoryManager()
    >>> manager.add(SystemPromptStep(content="You are helpful"))
    >>> manager.add(TaskStep(task="What is 2+2?"))
    >>> manager.to_messages()
    [{'role': 'system', 'content': 'You are helpful'}, {'role': 'user', 'content': 'What is 2+2?'}]
    """

    steps: list[Step] = field(default_factory=list)

    def add(self, step: Step) -> None:
        """
        Add a step to the memory.

        Parameters
        ----------
        step : Step
            The step to add
        """
        step.step_number = len(self.steps)
        self.steps.append(step)

    def to_messages(self) -> list[dict[str, str]]:
        """
        Convert all steps to a flat list of chat messages.

        Returns
        -------
        list[dict[str, str]]
            List of message dicts suitable for LLM API calls
        """
        messages: list[dict[str, str]] = []
        for step in self.steps:
            messages.extend(step.to_messages())
        return messages

    def prune(self, strategy: PruneStrategy) -> None:
        """
        Apply a pruning strategy to the steps.

        Parameters
        ----------
        strategy : PruneStrategy
            A callable that takes a list of steps and returns a pruned list
        """
        self.steps = strategy(self.steps)

    def get_steps_by_type(self, step_type: type[T]) -> list[T]:
        """
        Filter steps by type.

        Parameters
        ----------
        step_type : type[T]
            The step type to filter by

        Returns
        -------
        list[T]
            List of steps matching the given type
        """
        return [s for s in self.steps if isinstance(s, step_type)]

    def clear(self) -> None:
        """Clear all steps from memory."""
        self.steps.clear()

    @property
    def action_count(self) -> int:
        """
        Count the number of ActionSteps in memory.

        Returns
        -------
        int
            Number of ActionStep instances
        """
        return len(self.get_steps_by_type(ActionStep))


def keep_last_n_steps(n: int) -> PruneStrategy:
    """
    Create a pruning strategy that keeps the last N action steps.

    Always preserves SystemPromptStep and TaskStep regardless of N.

    Parameters
    ----------
    n : int
        Number of recent action steps to keep

    Returns
    -------
    PruneStrategy
        A pruning function
    """

    def _prune(steps: list[Step]) -> list[Step]:
        # Separate critical steps (system, task) from action steps
        critical: list[Step] = []
        actions: list[Step] = []

        for step in steps:
            if isinstance(step, (SystemPromptStep, TaskStep)):
                critical.append(step)
            else:
                actions.append(step)

        # Keep only last N action steps
        kept_actions = actions[-n:] if n > 0 else []

        # Rebuild step list maintaining original order
        result: list[Step] = []
        kept_set = set(id(a) for a in kept_actions)

        for step in steps:
            if isinstance(step, (SystemPromptStep, TaskStep)):
                result.append(step)
            elif id(step) in kept_set:
                result.append(step)

        return result

    return _prune


def prune_old_observations(keep_last_n: int = 3, max_length: int = 100) -> PruneStrategy:
    """
    Create a pruning strategy that truncates observations in older steps.

    Keeps full observations for the last N action steps, truncates older ones.
    Always preserves SystemPromptStep and TaskStep.

    Parameters
    ----------
    keep_last_n : int
        Number of recent action steps to keep full observations
    max_length : int
        Maximum observation length for older steps

    Returns
    -------
    PruneStrategy
        A pruning function
    """

    def _prune(steps: list[Step]) -> list[Step]:
        # Find all action steps
        action_indices: list[int] = []
        for i, step in enumerate(steps):
            if isinstance(step, ActionStep):
                action_indices.append(i)

        # Determine which action steps are "old" (not in last N)
        old_action_indices = (
            set(action_indices[:-keep_last_n]) if keep_last_n > 0 else set(action_indices)
        )

        # Truncate observations in old action steps
        for i in old_action_indices:
            step = steps[i]
            if isinstance(step, ActionStep):
                step.truncate(max_length)

        return steps

    return _prune


def no_pruning() -> PruneStrategy:
    """
    Create a pruning strategy that makes no changes (identity function).

    Returns
    -------
    PruneStrategy
        A no-op pruning function
    """

    def _prune(steps: list[Step]) -> list[Step]:
        return steps

    return _prune
