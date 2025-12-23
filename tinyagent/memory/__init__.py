"""
tinyagent.memory
Working memory for agent state across steps.

Public surface
--------------
AgentMemory  - Working memory scratchpad (original)
MemoryManager - Structured conversation memory with pruning
Step types   - SystemPromptStep, TaskStep, ActionStep, ScratchpadStep
Strategies   - keep_last_n_steps, prune_old_observations, no_pruning
"""

from .manager import (
    MemoryManager,
    PruneStrategy,
    keep_last_n_steps,
    no_pruning,
    prune_old_observations,
)
from .scratchpad import AgentMemory
from .steps import (
    ActionStep,
    ScratchpadStep,
    Step,
    SystemPromptStep,
    TaskStep,
)

__all__ = [
    # Original scratchpad memory
    "AgentMemory",
    # New structured memory
    "MemoryManager",
    "Step",
    "SystemPromptStep",
    "TaskStep",
    "ActionStep",
    "ScratchpadStep",
    # Pruning strategies
    "PruneStrategy",
    "keep_last_n_steps",
    "prune_old_observations",
    "no_pruning",
]
