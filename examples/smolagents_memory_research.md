# SmolAgents Memory System Research

**Generated:** 2025-12-23
**Purpose:** Understanding SmolAgents memory implementation to inform tinyAgent development

---

## Executive Summary

SmolAgents uses a clean, hierarchical step-based memory system with explicit separation of concerns. The architecture centers on typed Step classes, dual serialization methods (`dict()` for logging, `to_messages()` for LLM context), and a simple linear memory model without built-in pruning strategies.

**Key Insight:** SmolAgents prioritizes clarity over sophistication—no automatic pruning, no summarization, just straightforward message conversion with manual memory management when needed.

---

## 1. Step Class Architecture

### Base Class: MemoryStep

```python
@dataclass
class MemoryStep:
    def dict(self) -> dict:
        """Returns dataclass as dictionary via asdict()"""
        return asdict(self)

    def to_messages(self, summary_mode: bool = False) -> list[ChatMessage]:
        """Abstract method - must be implemented by subclasses"""
        raise NotImplementedError
```

**Design Pattern:** Abstract base with dual serialization
- `dict()` → Complete data for logging/debugging
- `to_messages()` → LLM-formatted conversation messages

### SystemPromptStep

```python
@dataclass
class SystemPromptStep(MemoryStep):
    system_prompt: str

    def to_messages(self, summary_mode: bool = False) -> list[ChatMessage]:
        if summary_mode:
            return []  # Exclude from summaries
        return [ChatMessage(role="system", content=self.system_prompt)]
```

**Key Decisions:**
- Single field: `system_prompt` (string)
- Summary mode returns empty list (system prompt only needed once)
- No images, no metadata

### TaskStep

```python
@dataclass
class TaskStep(MemoryStep):
    task: str
    task_images: list[PIL.Image.Image] | None

    def to_messages(self, summary_mode: bool = False) -> list[ChatMessage]:
        content = [{"type": "text", "text": self.task}]
        if self.task_images:
            for image in self.task_images:
                content.append({"type": "image", "image": image})
        return [ChatMessage(role="user", content=content)]
```

**Key Decisions:**
- Separates text task from optional images
- Uses structured content list (multi-modal ready)
- No summary mode special handling (tasks always included)

### ActionStep (Most Complex)

```python
@dataclass
class ActionStep(MemoryStep):
    step_number: int
    timing: Timing  # start_time, end_time, duration
    model_input_messages: list[ChatMessage] | None
    tool_calls: list[ToolCall] | None
    error: AgentError | None
    model_output_message: ChatMessage | None
    model_output: str | list[dict] | None
    code_action: str | None
    observations: str | None
    observations_images: list[PIL.Image.Image] | None
    action_output: Any
    token_usage: TokenUsage | None
    is_final_answer: bool
```

**Serialization (`dict()`):**
```python
def dict(self) -> dict:
    # Custom handling for complex types:
    # - Images → binary bytes via tobytes()
    # - action_output → make_json_serializable() utility
    # - token_usage → asdict()
    # - Preserves all fields for complete logging
```

**Message Conversion (`to_messages()`):**
```python
def to_messages(self, summary_mode: bool = False) -> list[ChatMessage]:
    messages = []

    # 1. Assistant message (model output)
    if not summary_mode and self.model_output:
        messages.append(ChatMessage(
            role="assistant",
            content=self.model_output
        ))

    # 2. Tool call message (function invocation)
    if self.tool_calls:
        messages.append(ChatMessage(
            role="assistant",
            tool_calls=self.tool_calls
        ))

    # 3. Observation images (if any)
    if self.observations_images:
        content = []
        for image in self.observations_images:
            content.append({"type": "image", "image": image})
        messages.append(ChatMessage(role="user", content=content))

    # 4. Tool response (observations)
    if self.observations:
        messages.append(ChatMessage(
            role="user",  # Note: uses "user" role for tool responses
            content=f"Tool returned: {self.observations}"
        ))

    # 5. Error handling with retry guidance
    if self.error:
        messages.append(ChatMessage(
            role="user",
            content=f"Error: {self.error}\n"
                   "Now let's retry: take care not to repeat previous errors!"
        ))

    return messages
```

**Key Design Decisions:**
1. **Rich metadata:** Captures timing, token usage, input messages for debugging
2. **Summary mode:** Skips assistant output to reduce context
3. **Image handling:** Separate images from text observations
4. **Error recovery:** Explicit retry instructions baked into error messages
5. **Role mapping:** Tool responses use "user" role (OpenRouter compatibility)

### PlanningStep

```python
@dataclass
class PlanningStep(MemoryStep):
    model_input_messages: list[ChatMessage]
    model_output_message: ChatMessage
    plan: str
    timing: Timing
    token_usage: TokenUsage | None

    def to_messages(self, summary_mode: bool = False) -> list[ChatMessage]:
        if summary_mode:
            return []  # Exclude plans from summaries
        return [
            ChatMessage(role="assistant", content=self.plan),
            ChatMessage(role="user", content="Proceed with the plan.")
        ]
```

**Key Decisions:**
- Planning excluded from summary mode (reduces noise)
- Returns assistant message + user directive to proceed
- Keeps full input/output for replay/debugging

### FinalAnswerStep

```python
@dataclass
class FinalAnswerStep(MemoryStep):
    output: Any

    # No to_messages() implementation
    # (Final answers don't need message conversion)
```

---

## 2. AgentMemory Container

### Structure

```python
class AgentMemory:
    def __init__(self, system_prompt: str):
        self.system_prompt: SystemPromptStep = SystemPromptStep(system_prompt)
        self.steps: list[TaskStep | ActionStep | PlanningStep] = []

    def reset(self):
        """Clear all steps but keep system prompt"""
        self.steps = []

    def get_succinct_steps(self) -> list[dict]:
        """Return steps without model_input_messages field"""
        # Excludes verbose input messages for cleaner logging

    def get_full_steps(self) -> list[dict]:
        """Return complete step data (all fields)"""

    def replay(self, detailed: bool = False):
        """Pretty-print execution trace
        - detailed=False: Shows step summaries
        - detailed=True: Shows full message history at each step
        """

    def return_full_code(self) -> str:
        """Concatenate all code_action strings from ActionSteps"""
```

**Design Pattern:** Simple list append
- No automatic pruning
- No summarization
- Manual management via direct access to `agent.memory.steps`

---

## 3. Message Conversion: `write_memory_to_messages()`

### Implementation (in Agent class)

```python
def write_memory_to_messages(
    self,
    summary_mode: bool = False,
) -> list[ChatMessage]:
    """Converts stored memory steps into LLM-compatible message format"""

    # Start with system prompt
    messages = self.memory.system_prompt.to_messages(summary_mode=summary_mode)

    # Convert each step to messages
    for memory_step in self.memory.steps:
        messages.extend(memory_step.to_messages(summary_mode=summary_mode))

    return messages
```

**Key Characteristics:**
1. **Linear iteration:** No chunking, no windowing
2. **Summary mode:** Global flag passed to all steps
3. **Flat list:** Returns simple list of ChatMessage objects
4. **No token counting:** No automatic truncation based on context limits

---

## 4. Pruning Strategies

### Current State: Manual Only

SmolAgents **does not have built-in pruning strategies**. The parameters `keep_last_n` and `prune_old_observations` mentioned in the research query do not exist in the codebase.

**Evidence from GitHub Issues:**

1. [Issue #901: Agent memory/history consolidation](https://github.com/huggingface/smolagents/issues/901)
   - "Agents maintain a history of every interaction... Over time this results in growing context size"
   - "Other applications deal with this by summarizing... or remembering only a limited history"
   - **Status:** Open feature request, no built-in solution yet

2. [Issue #694: Real Memory summary for ongoing conversations](https://github.com/huggingface/smolagents/issues/694)
   - Request for summarization to avoid LLM context limits
   - **Status:** Community discussion, no official implementation

3. [Issue #1121: Memory bank](https://github.com/huggingface/smolagents/issues/1121)
   - Advanced memory management feature request
   - **Status:** Proposal stage

### Manual Memory Management

**Pattern from documentation:**
```python
# Step-by-step execution with manual memory editing
agent.memory.steps.append(TaskStep(task=task, task_images=[]))

final_answer = None
step_number = 1
while final_answer is None and step_number <= 10:
    memory_step = ActionStep(
        step_number=step_number,
        observations_images=[],
    )
    final_answer = agent.step(memory_step)
    agent.memory.steps.append(memory_step)

    # Manual pruning example: Remove old observation images
    if step_number > 2:
        previous_step = agent.memory.steps[-3]
        if isinstance(previous_step, ActionStep):
            previous_step.observations_images = None  # Free memory

    step_number += 1
```

**Callback-based pruning:**
```python
from smolagents import ActionStep

def prune_old_images(memory_step: ActionStep, **kwargs):
    """Remove images from steps older than 2 steps back"""
    latest_step = memory_step.step_number
    for step in agent.memory.steps:
        if isinstance(step, ActionStep):
            if step.step_number < latest_step - 2:
                step.observations_images = None

agent.callback_registry.register(ActionStep, prune_old_images)
```

---

## 5. Truncation and Content Limiting

### truncate_content() Utility

```python
# Used in agents.py for limiting code output display
truncated_output = truncate_content(str(code_output.output))
observation = "Last output from code snippet:\n" + truncated_output
```

**Purpose:**
- Prevents excessively long execution results from overwhelming LLM
- Applied at observation formatting stage, not memory storage
- Preserves full output in ActionStep but shows truncated version in messages

**Not a memory pruning strategy** — this is output formatting, not history management.

---

## 6. Step Callbacks (Extension Point)

### CallbackRegistry

```python
class CallbackRegistry:
    def register(self, step_cls: type[MemoryStep], callback: Callable):
        """Associate callback with step type"""

    def callback(self, memory_step: MemoryStep, **kwargs):
        """Invoke matching handlers with backward compatibility"""
```

**Usage Pattern:**
```python
def log_action_step(step: ActionStep, **kwargs):
    print(f"Step {step.step_number}: {step.observations}")

agent.callback_registry.register(ActionStep, log_action_step)
```

**Enables:**
- Custom memory management per step type
- Side effects (logging, metrics, external storage)
- Manual pruning logic (as shown in section 4)

---

## 7. Serialization Details

### Image Handling

**In ActionStep.dict():**
```python
# Convert PIL images to binary bytes
if self.observations_images:
    serialized_images = [img.tobytes() for img in self.observations_images]
```

**In to_messages():**
```python
# Pass PIL image objects directly (assumes downstream handles serialization)
content.append({"type": "image", "image": image})
```

**Design Choice:**
- Binary serialization for logging/storage
- Object passing for LLM API calls (assumes API client handles image encoding)

### JSON Serialization

**make_json_serializable() utility:**
```python
# Applied to action_output in ActionStep.dict()
# Handles complex Python objects that aren't JSON-safe
# (No details in extracted code, but referenced in implementation)
```

---

## 8. Key Design Patterns for tinyAgent

### 1. Dual Serialization Methods
- **`dict()`** → Complete data for debugging/logging
- **`to_messages()`** → LLM-optimized conversation format
- **Why:** Separates storage concerns from context management

### 2. Summary Mode Flag
- Single boolean controls verbosity across all steps
- Allows same memory to generate full or condensed context
- **Implementation tip:** Pass through entire call chain

### 3. Typed Step Classes
- Explicit types for different execution phases
- Each step knows how to convert itself to messages
- **Benefit:** Easy to add new step types without modifying memory manager

### 4. Manual Memory Management
- No magic pruning algorithms
- User controls what stays via direct list access
- **Philosophy:** Simplicity over automation

### 5. Error Recovery in Messages
- Errors become messages with retry instructions
- LLM sees error context in next iteration
- **Pattern:** Transform errors into actionable feedback

### 6. Callback Extension Points
- Register handlers per step type
- Enables custom memory management without forking
- **Use case:** Metrics, external logging, custom pruning

### 7. Role Mapping for Tool Responses
- Uses "user" role for tool responses
- **Reason:** OpenRouter compatibility (mentioned in earlier searches)
- **Alternative:** Some systems use "tool" role (OpenAI native)

---

## 9. What SmolAgents Does NOT Have

1. **Automatic pruning strategies** (keep_last_n, prune_old_observations)
2. **Token-based truncation** (no max_tokens awareness in memory)
3. **Automatic summarization** (no LLM-based memory compression)
4. **Context window management** (will break if exceeding limits)
5. **Memory persistence** (no save/load functionality shown)
6. **Conversation branching** (linear history only)
7. **Memory search/retrieval** (no semantic search over past steps)

**Community Recognition:** Multiple GitHub issues acknowledge these gaps as future work.

---

## 10. Recommendations for tinyAgent

### Adopt from SmolAgents:

1. **Dual serialization pattern** (`dict()` + `to_messages()`)
   - Clean separation of logging vs LLM context
   - Easy debugging with full step data

2. **Typed Step classes with polymorphic `to_messages()`**
   - Clear structure
   - Easy to extend with new step types

3. **Summary mode flag**
   - Simple way to control context verbosity
   - No need for complex truncation logic initially

4. **Manual memory management as baseline**
   - Ship simple version first
   - Add automatic strategies as optional features

5. **Callback registry for extensibility**
   - Users can add custom memory management
   - No need to fork codebase

### Improve on SmolAgents:

1. **Add optional pruning strategies**
   - Implement `keep_last_n` as optional parameter
   - Add `max_tokens` awareness with automatic truncation
   - Make them opt-in, not mandatory

2. **Token counting in `write_memory_to_messages()`**
   - Track cumulative tokens
   - Warn or auto-truncate when approaching limits

3. **Memory compression utilities**
   - Provide optional summarization step
   - Keep in separate module (don't complicate core)

4. **Step importance scoring**
   - Mark certain steps as "always keep" (e.g., TaskStep, FinalAnswerStep)
   - Prune lower-importance steps first

5. **Structured observation formatting**
   - SmolAgents uses raw strings for observations
   - Consider structured format (success/error, metadata, result)

### Implementation Priority:

**Phase 1 (MVP):**
- Typed Step classes
- Dual serialization (dict + to_messages)
- AgentMemory container
- Manual management only

**Phase 2 (Usability):**
- Summary mode flag
- Optional `keep_last_n` pruning
- Token counting utilities

**Phase 3 (Advanced):**
- Callback registry
- Memory compression strategies
- Importance-based pruning

---

## 11. Code Examples for tinyAgent

### Minimal Step Implementation

```python
from dataclasses import dataclass, asdict
from typing import Any

@dataclass
class MemoryStep:
    """Base class for all memory steps"""

    def dict(self) -> dict:
        """Full serialization for logging"""
        return asdict(self)

    def to_messages(self, summary_mode: bool = False) -> list[dict]:
        """Convert to LLM messages - must override"""
        raise NotImplementedError

@dataclass
class ActionStep(MemoryStep):
    step_number: int
    thought: str
    action: str
    observation: str
    error: str | None = None

    def to_messages(self, summary_mode: bool = False) -> list[dict]:
        messages = []

        # Assistant thought + action
        if not summary_mode:
            messages.append({
                "role": "assistant",
                "content": f"Thought: {self.thought}\nAction: {self.action}"
            })

        # Tool response (observation)
        messages.append({
            "role": "user",
            "content": f"Observation: {self.observation}"
        })

        # Error with retry instruction
        if self.error:
            messages.append({
                "role": "user",
                "content": f"Error: {self.error}\nPlease try a different approach."
            })

        return messages
```

### Memory Container with Pruning

```python
class AgentMemory:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
        self.steps: list[MemoryStep] = []

    def add_step(self, step: MemoryStep):
        """Add step with optional auto-pruning"""
        self.steps.append(step)

    def to_messages(
        self,
        summary_mode: bool = False,
        keep_last_n: int | None = None,
        max_tokens: int | None = None
    ) -> list[dict]:
        """Convert memory to LLM messages with optional pruning"""

        # System prompt
        messages = [{"role": "system", "content": self.system_prompt}]

        # Determine which steps to include
        steps_to_include = self.steps
        if keep_last_n is not None:
            steps_to_include = self.steps[-keep_last_n:]

        # Convert steps
        for step in steps_to_include:
            messages.extend(step.to_messages(summary_mode=summary_mode))

        # Optional: Truncate by tokens (simplified - real impl needs tokenizer)
        if max_tokens is not None:
            messages = self._truncate_to_tokens(messages, max_tokens)

        return messages

    def _truncate_to_tokens(self, messages: list[dict], max_tokens: int) -> list[dict]:
        """Prune old messages to fit token budget"""
        # Placeholder - implement with actual tokenizer
        # Keep system prompt + last N messages that fit
        return messages
```

---

## 12. SmolAgents Source References

### Primary Source Files

1. **memory.py** (v1.21.0)
   - https://github.com/huggingface/smolagents/blob/v1.21.0/src/smolagents/memory.py
   - Contains all Step classes, AgentMemory, CallbackRegistry

2. **agents.py** (main branch)
   - https://github.com/huggingface/smolagents/blob/main/src/smolagents/agents.py
   - Contains `write_memory_to_messages()` implementation
   - Shows how memory is used in agent loop

3. **Memory Tutorial**
   - https://huggingface.co/docs/smolagents/en/tutorials/memory
   - Official documentation on memory management
   - Examples of manual step-by-step execution

### GitHub Issues (Memory Management)

1. **Issue #901** - Memory consolidation request
   - https://github.com/huggingface/smolagents/issues/901

2. **Issue #694** - Memory summary for long conversations
   - https://github.com/huggingface/smolagents/issues/694

3. **Issue #1121** - Memory bank proposal
   - https://github.com/huggingface/smolagents/issues/1121

4. **Issue #1224** - ActionStep.to_messages() regression
   - https://github.com/huggingface/smolagents/issues/1224
   - Shows real-world usage and compatibility concerns

---

## 13. Summary: Core Insights

### SmolAgents Philosophy
**Simple, explicit, manual** — No magic, no automatic optimization, just clear data structures and user control.

### Architecture Strengths
1. Clean separation of logging vs LLM context (dual serialization)
2. Typed steps with polymorphic message conversion
3. Easy to debug (full step data preserved)
4. Extensible via callbacks

### Architecture Limitations
1. No built-in context window management
2. Will fail on long conversations without manual intervention
3. No automatic memory optimization
4. Community recognizes these as future work

### For tinyAgent
- **Adopt:** Core architecture (typed steps, dual serialization, manual baseline)
- **Enhance:** Add optional automatic pruning strategies
- **Differentiate:** Built-in token awareness and smart truncation

### Design Decision Framework
When choosing memory strategies, balance:
- **Simplicity** (SmolAgents' strength) vs **Automation** (user convenience)
- **Transparency** (what's in memory is visible) vs **Magic** (auto-optimization)
- **Debugging** (full data preserved) vs **Performance** (minimal memory)

**Recommendation:** Start with SmolAgents' simple model, add optional smart features.

---

**Research completed:** 2025-12-23
**Confidence level:** High (based on official source code and documentation)
**Next steps:** Review this document with tinyAgent architecture goals, decide which patterns to adopt vs enhance.
