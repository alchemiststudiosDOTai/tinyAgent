"""
tinyagent.memory
Working memory for agent state across steps.

Public surface
--------------
AgentMemory  – dataclass
"""

from .scratchpad import AgentMemory

__all__ = ["AgentMemory"]
