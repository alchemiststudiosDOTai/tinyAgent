"""
tinyagent.core.memory
Simple message-based memory for conversations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["Memory"]


@dataclass
class Memory:
    """Simple message storage. Adapter controls format."""

    messages: list[dict[str, Any]] = field(default_factory=list)

    def add(self, message: dict[str, Any]) -> None:
        self.messages.append(message)

    def add_system(self, content: str) -> None:
        self.add({"role": "system", "content": content})

    def add_user(self, content: str) -> None:
        self.add({"role": "user", "content": content})

    def add_assistant(self, content: str) -> None:
        self.add({"role": "assistant", "content": content})

    def clear(self) -> None:
        self.messages.clear()

    def to_list(self) -> list[dict[str, Any]]:
        return list(self.messages)

    def __len__(self) -> int:
        return len(self.messages)
