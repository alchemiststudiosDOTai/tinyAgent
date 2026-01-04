---
title: Signals
path: tinyagent/signals/primitives.py
type: file
depth: 2
description: Cognitive primitives for LLM reasoning state communication
exports:
  - uncertain
  - explore
  - commit
seams: [E]
---

# Signals

Cognitive primitives that allow an LLM to communicate its internal reasoning state during execution, particularly in `TinyCodeAgent`.

## Overview

Signals provide visibility into the agent's "thought process" by exposing explicit communication primitives that can be called from generated code.

## Available Signals

### uncertain(message: str)

Signal uncertainty about data, approaches, or observations.

**Purpose:** Indicate when the agent is unsure about something.

**Use Cases:**
- Ambiguous data format
- Unclear requirements
- Multiple possible approaches
- Missing information

**Example:**
```python
# In agent's generated code
uncertain("Data format is unclear - could be CSV or JSON")
```

### explore(message: str)

Signal exploration or investigation of structure/assumptions.

**Purpose:** Indicate active investigation before committing to a solution.

**Use Cases:**
- Testing assumptions
- Investigating data structure
- Exploring possible solutions
- Prototype development

**Example:**
```python
# In agent's generated code
explore("Testing if data is in CSV format by checking for commas")
```

### commit(message: str)

Signal confidence and readiness to provide final answer.

**Purpose:** Indicate verification complete and final answer ready.

**Use Cases:**
- Verified assumptions
- Completed analysis
- Ready to finalize
- Confident in result

**Example:**
```python
# In agent's generated code
commit("Analysis complete - final answer is 42")
```

## Signal Internals

### Signal Class

```python
@dataclass
class Signal:
    """Internal signal representation."""
    type: SignalType
    message: str
    timestamp: datetime
```

### SignalType Enum

```python
class SignalType(Enum):
    """Types of signals."""
    UNCERTAIN = "uncertain"
    EXPLORE = "explore"
    COMMIT = "commit"
```

### Signal Collector

Global collector that captures signals:

```python
_signal_collector: list[Signal] = []
```

## Integration with TinyCodeAgent

### Injection into Execution Environment

```python
class TinyCodeAgent:
    def _inject_signals(self, executor: Executor):
        """Inject signal functions into execution environment."""
        executor.inject("uncertain", uncertain)
        executor.inject("explore", explore)
        executor.inject("commit", commit)
```

### Usage in Generated Code

The agent's LLM is prompted to use signals:

```python
# Agent's generated code
def solve_task():
    # Exploring data structure
    explore("Checking if data is CSV format")

    if not has_header:
        uncertain("Can't determine if CSV has header")

    # After analysis
    commit("Final answer: 42")
```

### Signal Collection

```python
# Before execution
agent._signal_collector = []

# During execution (called from generated code)
uncertain("Not sure about data format")  # Added to collector

# After execution
signals = agent._signal_collector  # List of Signal objects
```

## Usage Examples

### Basic Usage

```python
from tinyagent import TinyCodeAgent

agent = TinyCodeAgent()

result = agent.run_sync("Analyze this data and tell me the mean")

# Check signals captured during execution
for signal in agent._signal_collector:
    print(f"{signal.type.value}: {signal.message}")
```

### Signal Flow in Execution

```python
# 1. Agent generates code
code = """
explore("Testing data format")
if is_csv:
    commit("Data is CSV format")
else:
    uncertain("Unknown data format")
"""

# 2. Code executes with signals injected
executor.inject("explore", explore)
executor.inject("uncertain", uncertain)
executor.inject("commit", commit)

# 3. Signals collected during execution
explore("Testing data format")  # Signal captured
commit("Data is CSV format")    # Signal captured

# 4. Signals available for analysis
signals = agent._signal_collector
# [Signal(type=EXPLORE, message="Testing data format"),
#  Signal(type=COMMIT, message="Data is CSV format")]
```

### Verbose Output

When `verbose=True`, signals are printed:

```python
agent = TinyCodeAgent(verbose=True)
agent.run_sync("Analyze data")

# Output:
# [SIGNAL] EXPLORE: Testing data format
# [SIGNAL] COMMIT: Data is CSV format
```

## Prompt Integration

Signals are mentioned in the system prompt for `TinyCodeAgent`:

```python
# From prompts/templates.py
CODE_SYSTEM = """
You have access to signals for cognitive communication:
- uncertain(message): Signal uncertainty about data/approaches
- explore(message): Signal exploration/investigation
- commit(message): Signal confidence and final answer

Use these to communicate your reasoning process.
"""
```

## Best Practices

### When to Use Each Signal

**uncertain:**
- Data format ambiguity
- Missing information
- Multiple valid interpretations
- External dependencies unclear

**explore:**
- Testing hypotheses
- Investigating structure
- Prototype implementations
- Validation attempts

**commit:**
- Verification complete
- Final answer ready
- Analysis finished
- Confidence established

### Signal Frequency

**Good Signal Usage:**
```python
explore("Checking data format")
# ... investigation ...
commit("Data is CSV with 3 columns")
```

**Over-signaling:**
```python
uncertain("Not sure")
explore("Checking")
uncertain("Still not sure")
explore("Checking again")
# Too many signals, adds noise
```

### Message Quality

**Good Messages:**
```python
uncertain("Data could be CSV or JSON - need to check structure")
explore("Testing CSV format by looking for comma separators")
commit("Confirmed CSV format with 3 columns")
```

**Vague Messages:**
```python
uncertain("Not sure")
explore("Checking")
commit("Done")
# Doesn't provide useful context
```

## Debugging with Signals

Signals provide visibility into agent reasoning:

```python
agent = TinyCodeAgent(verbose=True)
result = agent.run_sync("Complex task")

# Review signals to understand agent's thought process
for signal in agent._signal_collector:
    print(f"{signal.type.value.upper()}: {signal.message}")

# Use this to:
# - Debug why agent made certain decisions
# - Understand uncertainty points
# - Identify exploration strategies
# - Verify final answer confidence
```

## Integration with Other Systems

### With AgentMemory

```python
# Signals can work with memory
uncertain("Data format unclear")
memory.observe("Attempted CSV parsing - failed")

explore("Trying JSON format instead")
memory.observe("JSON parsing successful")

commit("Data is JSON format")
memory.store("format", "json")
```

### With Final Answer

```python
# Signal before final answer
explore("Calculating final result")
result = calculate()
commit(f"Final answer: {result}")

# Actual final answer
final_answer(result)
```

## Error Handling

Signals are safe to call and won't interrupt execution:

```python
# Signal collector handles errors gracefully
uncertain("This message will be recorded")
explore("Even if other code fails")
try:
    risky_operation()
except Exception:
    uncertain("Operation failed - trying alternative")
# Agent continues execution
```

## Implementation Details

### Thread Safety

Signals use a global collector (not thread-safe):

```python
# Not safe for concurrent execution
agent1 = TinyCodeAgent()
agent2 = TinyCodeAgent()

# These would share the same signal collector
# Use separate processes for true isolation
```

### Performance Overhead

Minimal overhead:
- Signal creation: O(1)
- List append: O(1) amortized
- Memory usage: O(n) where n = signal count

### Reset Between Runs

Signals are reset for each agent run:

```python
# Run 1
agent.run_sync("Task 1")
signals1 = agent._signal_collector  # Signals from task 1

# Run 2
agent.run_sync("Task 2")
signals2 = agent._signal_collector  # Only signals from task 2
```

## Future Enhancements

Potential improvements:
- Structured signal data (not just messages)
- Signal filtering/levels
- Signal-based agent control flow
- Signal aggregation and analysis
- Visual signal timeline representation
