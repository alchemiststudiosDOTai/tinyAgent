---
title: Step History Tracking
path: memory/steps.py
type: file
depth: 1
description: Structured conversation history with typed Step objects and message conversion
seams: [Step.to_messages(), SystemPromptStep, TaskStep, ActionStep, ScratchpadStep]
---

# Step History Tracking

## Overview

Step history tracking provides a structured, typed approach to recording conversation flow. Each interaction is represented as a `Step` object with specific metadata and conversion capabilities.

## Step Hierarchy

```
Step (base)
├── SystemPromptStep
├── TaskStep
├── ActionStep
└── ScratchpadStep
```

## Base Step Class

**Location**: `memory/steps.py`

```python
@dataclass
class Step:
    timestamp: float = field(default_factory=time.time)
    step_number: int = 0

    def to_messages(self) -> list[dict[str, str]]:
        return []
```

### Attributes

- **timestamp**: Unix timestamp of step creation
- **step_number**: Sequential index in conversation history

### Methods

**to_messages()**: Convert step to LLM-compatible message format
- Returns empty list by default
- Overridden by subclasses to provide specific format

## Step Types

### 1. SystemPromptStep

**Purpose**: Represents initial system instructions to the LLM.

```python
@dataclass
class SystemPromptStep(Step):
    content: str

    def to_messages(self) -> list[dict[str, str]]:
        return [{"role": "system", "content": self.content}]
```

**Attributes**:
- `content`: System prompt text

**Message Format**:
```python
[{"role": "system", "content": "You are a helpful assistant."}]
```

**Usage**:
```python
step = SystemPromptStep(content="You are a code analysis expert.")
manager.add(step)
```

**Lifecycle**:
- Created once at agent initialization
- Never pruned (preserved by all pruning strategies)
- Converted to system message for LLM

### 2. TaskStep

**Purpose**: Represents the user's initial query or instruction.

```python
@dataclass
class TaskStep(Step):
    task: str

    def to_messages(self) -> list[dict[str, str]]:
        return [{"role": "user", "content": self.task}]
```

**Attributes**:
- `task`: User's task description or question

**Message Format**:
```python
[{"role": "user", "content": "Analyze this Python code for bugs."}]
```

**Usage**:
```python
step = TaskStep(task="Help me optimize this function.")
manager.add(step)
```

**Lifecycle**:
- Created once at agent initialization
- Never pruned (preserved by all pruning strategies)
- Provides primary context for agent

### 3. ActionStep

**Purpose**: Represents an agent action (tool call) and its result.

```python
@dataclass
class ActionStep(Step):
    thought: str | None = None
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    observation: str = ""
    error: str | None = None
    is_final: bool = False
    raw_llm_response: str = ""
```

**Attributes**:
- `thought`: Agent's reasoning (optional)
- `tool_name`: Name of tool called
- `tool_args`: Arguments passed to tool
- `observation`: Result from tool execution
- `error`: Error message if execution failed
- `is_final`: Whether this is the final action
- `raw_llm_response`: Full LLM response text

**Methods**:

**to_messages()**: Convert to message format
```python
def to_messages(self) -> list[dict[str, str]]:
    messages = []

    # LLM response as assistant message
    if self.raw_llm_response:
        messages.append({"role": "assistant", "content": self.raw_llm_response})

    # Observation or error as user message (OpenRouter compatibility)
    content = ""
    if self.error:
        content = f"Error: {self.error}"
    elif self.observation:
        content = f"Observation: {self.observation}"

    if content:
        messages.append({"role": "user", "content": content})

    return messages
```

**truncate(max_length: int)**: Shorten observation string
```python
def truncate(self, max_length: int) -> None:
    if len(self.observation) > max_length:
        self.observation = self.observation[:max_length]
```

**Message Format**:
```python
# Successful action
[
    {"role": "assistant", "content": "I'll read the file."},
    {"role": "user", "content": "Observation: File content here..."}
]

# Failed action
[
    {"role": "assistant", "content": "I'll try to connect to the API."},
    {"role": "user", "content": "Error: Connection timeout"}
]
```

**Usage**:
```python
step = ActionStep(
    raw_llm_response="I'll check the file size.",
    tool_name="file_stat",
    tool_args={"path": "/tmp/file.txt"},
    observation="Size: 1024 bytes",
    is_final=False
)
manager.add(step)
```

**Lifecycle**:
- Created for each tool execution
- Primary target for pruning strategies
- Can be truncated to reduce token usage
- May be removed entirely in aggressive pruning

**OpenRouter Compatibility**:
- Uses `user` role for observations (not `tool` role)
- Ensures compatibility with various LLM providers

### 4. ScratchpadStep

**Purpose**: Captures internal working notes or thoughts.

```python
@dataclass
class ScratchpadStep(Step):
    content: str
    raw_llm_response: str

    def to_messages(self) -> list[dict[str, str]]:
        return [
            {"role": "assistant", "content": self.raw_llm_response},
            {"role": "user", "content": f"Scratchpad noted: {self.content}"}
        ]
```

**Attributes**:
- `content`: The scratchpad note
- `raw_llm_response`: LLM response that generated the note

**Message Format**:
```python
[
    {"role": "assistant", "content": "I should note this important finding."},
    {"role": "user", "content": "Scratchpad noted: The algorithm has O(n^2) complexity."}
]
```

**Usage**:
```python
step = ScratchpadStep(
    content="Need to verify file permissions first",
    raw_llm_response="I should check permissions before reading."
)
manager.add(step)
```

**Lifecycle**:
- Created when agent wants to remember something
- Not currently handled by pruning strategies
- Provides persistent context across steps

## Step Numbering

**Assignment**: Done automatically by `MemoryManager.add()`

```python
def add(self, step: Step) -> None:
    step.step_number = len(self.steps)
    self.steps.append(step)
```

**Pattern**:
- SystemPromptStep: 0
- TaskStep: 1
- ActionStep/ScratchpadStep: 2, 3, 4, ...

**Usage**:
```python
# Filter by step number
recent_steps = [s for s in manager.steps if s.step_number > 10]

# Debug specific step
step = manager.steps[5]
print(f"Step {step.step_number}: {step}")
```

## Timestamp Tracking

**Assignment**: Done automatically at step creation

```python
timestamp: float = field(default_factory=time.time)
```

**Format**: Unix timestamp (seconds since epoch)

**Usage**:
```python
# Filter by time
from datetime import datetime
recent_steps = [s for s in manager.steps
                if s.timestamp > time.time() - 3600]  # Last hour

# Format for display
dt = datetime.fromtimestamp(step.timestamp)
print(f"Step created at {dt}")
```

## Message Conversion Pipeline

### From Steps to Messages

```python
# MemoryManager.to_messages()
def to_messages(self) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for step in self.steps:
        messages.extend(step.to_messages())
    return messages
```

### Example Conversation

**Steps**:
1. SystemPromptStep("You are a helpful assistant.")
2. TaskStep("What is the capital of France?")
3. ActionStep(raw_llm_response="I'll search for this.", tool_name="search", observation="Paris")
4. ActionStep(raw_llm_response="The answer is Paris.", is_final=True)

**Messages**:
```python
[
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"},
    {"role": "assistant", "content": "I'll search for this."},
    {"role": "user", "content": "Observation: Paris"},
    {"role": "assistant", "content": "The answer is Paris."}
]
```

## Step Filtering

### By Type

```python
# Get all action steps
actions = manager.get_steps_by_type(ActionStep)

# Get all scratchpad notes
notes = manager.get_steps_by_type(ScratchpadStep)

# Count by type
action_count = len(manager.get_steps_by_type(ActionStep))
```

### By Properties

```python
# Get failed actions
failed_actions = [s for s in manager.steps
                  if isinstance(s, ActionStep) and s.error]

# Get final action
final_action = next((s for s in manager.steps
                     if isinstance(s, ActionStep) and s.is_final), None)

# Get recent actions
recent_actions = [s for s in manager.steps
                  if isinstance(s, ActionStep) and s.step_number > 10]
```

### Custom Filtering

```python
def filter_steps(
    steps: list[Step],
    step_types: list[type[Step]] | None = None,
    after_step: int | None = None,
    before_step: int | None = None,
    with_error: bool | None = None
) -> list[Step]:
    filtered = steps

    # Filter by type
    if step_types:
        filtered = [s for s in filtered if type(s) in step_types]

    # Filter by step number range
    if after_step is not None:
        filtered = [s for s in filtered if s.step_number > after_step]
    if before_step is not None:
        filtered = [s for s in filtered if s.step_number < before_step]

    # Filter by error status
    if with_error is not None:
        filtered = [s for s in filtered
                    if isinstance(s, ActionStep) and
                    (bool(s.error) == with_error)]

    return filtered

# Usage
recent_actions = filter_steps(
    manager.steps,
    step_types=[ActionStep],
    after_step=5,
    with_error=False
)
```

## Step Serialization

### For Persistence

```python
import json
from dataclasses import asdict

# Convert to dict
step_dict = {
    "type": "ActionStep",
    "data": asdict(step)
}

# Serialize to JSON
json_str = json.dumps(step_dict)

# Save to file
with open("step.json", "w") as f:
    json.dump(step_dict, f)
```

### From JSON

```python
def step_from_dict(data: dict) -> Step:
    step_type = data["type"]
    step_data = data["data"]

    if step_type == "SystemPromptStep":
        return SystemPromptStep(**step_data)
    elif step_type == "TaskStep":
        return TaskStep(**step_data)
    elif step_type == "ActionStep":
        return ActionStep(**step_data)
    elif step_type == "ScratchpadStep":
        return ScratchpadStep(**step_data)
    else:
        raise ValueError(f"Unknown step type: {step_type}")
```

## Debugging Steps

### Print Step Summary

```python
def summarize_step(step: Step) -> str:
    if isinstance(step, SystemPromptStep):
        return f"SystemPrompt: {step.content[:50]}..."
    elif isinstance(step, TaskStep):
        return f"Task: {step.task[:50]}..."
    elif isinstance(step, ActionStep):
        status = "ERROR" if step.error else "OK"
        return f"Action: {step.tool_name} ({status})"
    elif isinstance(step, ScratchpadStep):
        return f"Scratchpad: {step.content[:50]}..."
    else:
        return f"Unknown: {type(step).__name__}"

# Usage
for step in manager.steps:
    print(f"[{step.step_number}] {summarize_step(step)}")
```

### Visualize Timeline

```python
from datetime import datetime

def visualize_timeline(steps: list[Step]) -> None:
    print("Conversation Timeline:")
    print("-" * 60)
    for step in steps:
        dt = datetime.fromtimestamp(step.timestamp).strftime("%H:%M:%S")
        print(f"[{dt}] [{step.step_number}] {summarize_step(step)}")

# Usage
visualize_timeline(manager.steps)
```

## Best Practices

### 1. Use Appropriate Step Types
- SystemPromptStep: For initial setup
- TaskStep: For user queries
- ActionStep: For tool executions
- ScratchpadStep: For internal notes

### 2. Preserve Critical Steps
- SystemPromptStep and TaskStep are never pruned
- ActionSteps are primary pruning targets
- Consider importance when creating custom strategies

### 3. Track Step Metadata
- Use step numbers for ordering
- Use timestamps for debugging
- Use type information for filtering

### 4. Validate Message Conversion
- Ensure to_messages() returns valid format
- Test with actual LLM API
- Handle edge cases (empty content, None values)

### 5. Consider Serialization
- Design steps with persistence in mind
- Use simple, serializable types
- Document serialization format
