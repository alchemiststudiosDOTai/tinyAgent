---
title: Cognitive Signals
path: signals/
type: directory
depth: 1
description: LLM cognitive state communication primitives for transparency and observability
exports: [Signal, SignalType, uncertain, explore, commit, set_signal_collector]
seams: [M]
---

# signals/

## Where
`/Users/tuna/tinyAgent/tinyagent/signals/`

## What
Defines and emits "cognitive signals" from LLM during execution. Provides visibility into LLM's reasoning process, indicating uncertainty, exploration, or commitment to particular paths.

## How

### primitives.py

**Key Classes:**

**SignalType (Enum)**
Three cognitive signal types:
- `UNCERTAIN`: LLM unsure about data format, approach, or meanings
- `EXPLORE`: LLM investigating, testing assumptions, gathering information
- `COMMIT`: LLM confident, verified assumptions, ready to proceed

**Signal (dataclass, frozen=True)**
Encapsulates emitted signal:
- `signal_type (SignalType)`: Category of signal
- `message (str)`: Descriptive message
- `__str__()`: Readable representation

**Key Functions:**

**set_signal_collector(collector: Callable[[Signal], None] | None) -> None**
- Registers callback invoked when signal emitted
- Allows external component to collect and process signals
- Decouples emission from handling

**Signal Emission Functions:**
- `uncertain(message: str) -> Signal`: Emits UNCERTAIN signal
- `explore(message: str) -> Signal`: Emits EXPLORE signal
- `commit(message: str) -> Signal`: Emits COMMIT signal

**Pattern:**
1. Executor registers signal collector
2. LLM code calls signal functions (e.g., `uncertain("data format unclear")`)
3. Collector receives and processes signal
4. System observes LLM's cognitive state

### __init__.py

**Exports:**
- `uncertain`, `explore`, `commit` from primitives.py

**Purpose:**
- Simplifies imports: `from tinyagent.signals import uncertain`
- Public interface for signals package

## Why

**Design Rationale:**
- **Visibility**: Makes LLM's thinking process transparent
- **Modularity**: Separates signal definition, emission, and handling
- **Decoupling**: Collector mechanism decouples emission from processing
- **Observability**: Critical for debugging, monitoring, adaptive behavior

**Architectural Role:**
- **Communication Bridge**: Connects LLM reasoning to execution environment
- **Executor Integration**: Used by `execution/local.py` to observe state
- **Adaptive Behavior**: Enables system to react to LLM confidence levels
- **Debugging**: Provides insight into decision-making process

**Dependencies:**
- `enum`: SignalType enumeration
- `dataclasses`: Signal structure
- `typing`: Callable and optional types
- `threading`: Thread-safe collector storage
