---
title: Signals
path: signals/
type: directory
depth: 0
description: LLM communication primitives for uncertainty and exploration signaling
seams: [Signal, SignalType, SignalCollector]
---

## Directory Purpose and Organization

The `signals` directory provides communication primitives for the Large Language Model (LLM) to express its cognitive state (uncertainty, exploration, confidence) during execution. This offers crucial visibility into its reasoning process, aiding in introspection and debugging of the agent's behavior.

The directory is organized into:

- **`__init__.py`**: Serves as the package's public interface
- **`primitives.py`**: Contains the core implementation of signaling mechanisms

## Naming Conventions

- **Module Names**: Descriptive and lowercase (e.g., `primitives.py`)
- **Classes**: PascalCase (e.g., `Signal`, `SignalType`)
- **Enums**: PascalCase for enum names, SCREAMING_SNAKE_CASE for members (e.g., `SignalType.UNCERTAIN`)
- **Functions**: lowercase_with_underscores (e.g., `uncertain`, `explore`, `commit`, `set_signal_collector`)
- **Internal Variables**: Leading underscore for module-private variables (e.g., `_signal_collector`)
- **Public API**: Explicitly managed using `__all__` in `__init__.py` and `primitives.py`

## Relationship to Sibling Directories

`signals` is a core utility module within the `tinyagent` framework:

- **`agents`**: Agents (particularly `TinyCodeAgent`) use signals to communicate their internal state during execution
- **`execution`**: The execution environment integrates signal collection to provide visibility into agent reasoning
- **`memory`**: Potentially used to track signaling patterns for analysis
- **`observability`**: Future integration with tracing and metrics (when implemented)

It acts as a common, project-wide mechanism for LLM introspection and state communication.

## File Structure and Architecture

### `signals/__init__.py`

Serves as the package's public interface, selectively exposing:

- `commit`: Function to signal confidence/final answer
- `explore`: Function to signal exploratory behavior
- `uncertain`: Function to signal uncertainty

These are imported from `primitives.py` and exposed via `__all__`.

### `signals/primitives.py`

Contains the core implementation:

#### `SignalType` (Enum)

Defines the discrete states an LLM can signal:

- **`UNCERTAIN`**: The LLM is unsure about its current approach or answer
- **`EXPLORE`**: The LLM is actively exploring different possibilities or approaches
- **`COMMIT`**: The LLM is confident in its answer or approach

#### `Signal` (Dataclass)

A data structure representing an emitted signal:

- `signal_type`: The type of signal (from `SignalType` enum)
- `message`: A descriptive message explaining the reasoning

#### `_signal_collector`

A mutable reference to a callable that processes emitted `Signal` objects:

- Set externally via `set_signal_collector()`
- Implements a simple observer pattern
- Allows flexible handling of signals by different execution environments

#### Signal Emission Functions

- **`set_signal_collector(collector)`**: Configures the `_signal_collector` callable
  - Pass `None` to clear the collector
  - Pass a callable to receive signals

- **`uncertain(message)`**: Creates and emits an `UNCERTAIN` signal
- **`explore(message)`**: Creates and emits an `EXPLORE` signal
- **`commit(message)`**: Creates and emits a `COMMIT` signal

Each signal function:
1. Creates a `Signal` instance with the appropriate type and message
2. Calls the `_signal_collector` if one is set
3. Returns for immediate use in code

## Architecture Summary

The `signals` directory implements a clean observer pattern that:

1. **Separates API exposure from core logic**: `__init__.py` provides the public interface, `primitives.py` contains implementation
2. **Enables flexible signal handling**: The collector pattern allows different execution environments to handle signals differently
3. **Provides cognitive visibility**: Gives insight into the LLM's reasoning process
4. **Supports introspection and debugging**: Helps understand agent decision-making

Example usage in code:

```python
from tinyagent.signals import uncertain, explore, commit

# In agent code
def solve(problem):
    if not clear_approach:
        uncertain("No clear solution path identified")
        explore("Trying multiple approaches")

    if solution_found:
        commit("Found valid solution")
```
