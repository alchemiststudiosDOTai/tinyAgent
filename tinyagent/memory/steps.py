"""
tinyagent.memory.steps
Step type hierarchy for structured conversation memory.

Public surface
--------------
Step           - Base step class
SystemPromptStep - System prompt message
TaskStep       - User task/question
ActionStep     - Tool call with observation/error
ScratchpadStep - Working memory notes
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "Step",
    "SystemPromptStep",
    "TaskStep",
    "ActionStep",
    "ScratchpadStep",
]


@dataclass
class Step:
    """
    Base class for all step types in the memory system.

    Parameters
    ----------
    timestamp : float
        Unix timestamp when the step was created
    step_number : int
        Sequential step number in the conversation
    """

    timestamp: float = field(default_factory=time.time)
    step_number: int = 0

    def to_messages(self) -> list[dict[str, str]]:
        """
        Convert this step to a list of chat messages.

        Returns
        -------
        list[dict[str, str]]
            List of message dicts with 'role' and 'content' keys
        """
        return []


@dataclass
class SystemPromptStep(Step):
    """
    Represents the system prompt at the start of a conversation.

    Parameters
    ----------
    content : str
        The system prompt text
    """

    content: str = ""

    def to_messages(self) -> list[dict[str, str]]:
        """Convert to a system message."""
        return [{"role": "system", "content": self.content}]


@dataclass
class TaskStep(Step):
    """
    Represents the user's task or question.

    Parameters
    ----------
    task : str
        The user's task or question text
    """

    task: str = ""

    def to_messages(self) -> list[dict[str, str]]:
        """Convert to a user message."""
        return [{"role": "user", "content": self.task}]


@dataclass
class ActionStep(Step):
    """
    Represents a single action step with tool call and result.

    Parameters
    ----------
    thought : str
        The agent's reasoning before the action
    tool_name : str
        Name of the tool being called
    tool_args : dict[str, Any]
        Arguments passed to the tool
    observation : str
        Result from the tool (if successful)
    error : str
        Error message (if tool failed)
    is_final : bool
        Whether this step contains the final answer
    raw_llm_response : str
        The raw LLM output for this step
    """

    thought: str = ""
    tool_name: str = ""
    tool_args: dict[str, Any] = field(default_factory=dict)
    observation: str = ""
    error: str = ""
    is_final: bool = False
    raw_llm_response: str = ""

    def truncate(self, max_length: int = 500) -> None:
        """
        Truncate the observation to a maximum length.

        Parameters
        ----------
        max_length : int
            Maximum length for the observation string
        """
        if len(self.observation) > max_length:
            self.observation = self.observation[:max_length] + "..."

    def to_messages(self) -> list[dict[str, str]]:
        """
        Convert to assistant message followed by user observation/error.

        Uses 'user' role for tool responses for OpenRouter compatibility.
        """
        messages: list[dict[str, str]] = []

        if self.raw_llm_response:
            messages.append({"role": "assistant", "content": self.raw_llm_response})

        if self.error:
            messages.append({"role": "user", "content": self.error})
        elif self.observation:
            messages.append({"role": "user", "content": f"Observation: {self.observation}"})

        return messages


@dataclass
class ScratchpadStep(Step):
    """
    Represents a scratchpad note for working memory.

    Parameters
    ----------
    content : str
        The scratchpad content (agent's working notes)
    raw_llm_response : str
        The raw LLM output that contained the scratchpad
    """

    content: str = ""
    raw_llm_response: str = ""

    def to_messages(self) -> list[dict[str, str]]:
        """
        Convert to assistant message followed by acknowledgment.

        Returns both the raw response and an acknowledgment message.
        """
        messages: list[dict[str, str]] = []

        if self.raw_llm_response:
            messages.append({"role": "assistant", "content": self.raw_llm_response})

        messages.append({"role": "user", "content": f"Scratchpad noted: {self.content}"})

        return messages
