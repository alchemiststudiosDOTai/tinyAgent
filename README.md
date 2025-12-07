# tinyAgent

![tinyAgent Logo](static/images/new-ta-logo.jpg)

**Build AI agents that actually work.** Turn any Python function into an autonomous tool with a single decorator.

```python
from tinyagent import tool, ReactAgent

@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b

@tool
def divide(a: float, b: float) -> float:
    """Divide two numbers."""
    return a / b

agent = ReactAgent(tools=[multiply, divide])
result = agent.run("What is 12 times 5, then divided by 3?")
# → 20
```

**That's it.** The agent reasons through the steps:
1. Calls `multiply(12, 5)` → 60
2. Calls `divide(60, 3)` → 20
3. Returns the answer

## Why tinyAgent?

| Feature | Benefit |
|---------|---------|
| **Zero boilerplate** | Just decorate functions with `@tool` |
| **Auto-reasoning** | Agent figures out which tools to call and when |
| **LLM-agnostic** | Works with OpenRouter, OpenAI, Claude, Llama, etc. |
| **Type-safe** | Full type hints and validation built-in |
| **Production-ready** | Error handling, retries, and observability |

## Installation

```bash
# Recommended: UV (10x faster venv creation)
uv venv && source .venv/bin/activate
uv pip install tiny_agent_os

# Or with pip
pip install tiny_agent_os
```

## Quick Start

**1. Get an API key** from [openrouter.ai](https://openrouter.ai)

**2. Set environment variables:**
```bash
export OPENAI_API_KEY=your_key_here
export OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

**3. Create your first agent:**
```python
from tinyagent import tool, ReactAgent

@tool
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b

agent = ReactAgent(tools=[add])
print(agent.run("What is 5 plus 3?"))
```

> **Note**: This is a clean rewrite focused on keeping tinyAgent truly tiny. For the legacy codebase (v0.72.x), install with `pip install tiny-agent-os==0.72.18` or see the [`0.72` branch](https://github.com/alchemiststudiosDOTai/tinyAgent/tree/0.72).

## Package Structure

As of v0.73, tinyAgent's internal structure has been reorganized for better maintainability:

- `tinyagent/agent.py` → `tinyagent/agents/agent.py` (ReactAgent)
- `tinyagent/code_agent.py` → `tinyagent/agents/code_agent.py` (TinyCodeAgent)

The public API remains unchanged - you can still import directly from `tinyagent`:
```python
from tinyagent import ReactAgent, TinyCodeAgent, tool
```

## Choose Your Model

tinyAgent supports any LLM via OpenRouter:

```python
from tinyagent import ReactAgent

# Cheap & fast
agent = ReactAgent(tools=[...], model="gpt-4o-mini")

# Most capable
agent = ReactAgent(tools=[...], model="anthropic/claude-3.5-sonnet")

# Open source
agent = ReactAgent(tools=[...], model="meta-llama/llama-3.1-70b-instruct")
```

**Default:** Uses `gpt-4o-mini` if no model is specified.

## Examples

### Example 1: Multi-Step Math
```python
from tinyagent import tool, ReactAgent

@tool
def percent(value: float, pct: float) -> float:
    """Calculate percentage of a value."""
    return value * (pct / 100)

@tool
def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b

agent = ReactAgent(tools=[percent, subtract])
result = agent.run("If I have 15 apples and give away 40%, how many are left?")
# Agent: calculates 40% of 15 (6) → subtracts (15 - 6 = 9) → answers "9 apples left"
```

### Example 2: Web Search
```python
from tinyagent import ReactAgent
from tinyagent.tools.builtin import web_search

agent = ReactAgent(tools=[web_search])
result = agent.run("Compare FastAPI vs Django performance")

# Set your key first:
export BRAVE_SEARCH_API_KEY=your_key
```

### Example 3: Python Code Execution
```python
from tinyagent import TinyCodeAgent

agent = TinyCodeAgent(tools=[])
result = agent.run("Generate 10 random numbers and show the average")
# Agent writes and executes Python code to solve this
```

## Core Concepts

### ReactAgent — Tool Orchestration
- Reasons through multi-step problems
- Automatically chains tool calls
- Includes retry logic and error handling

```python
agent = ReactAgent(tools=[multiply, divide])
agent.run("What is 100 divided by 5, times 3?")
```

### TinyCodeAgent — Code Execution
- Writes and executes Python code
- Sandboxed with restricted imports
- Perfect for data processing and calculations

```python
agent = TinyCodeAgent()
agent.run("Generate 100 random numbers and show the median")
```

### Tools — Your Building Blocks
Create tools by decorating functions:

```python
@tool
def fetch_data(id: int) -> dict:
    """Fetch user data by ID."""
    return {"id": id, "name": "Alice"}

@tool
def format_csv(data: list) -> str:
    """Convert list to CSV format."""
    return ",".join(str(d) for d in data)
```

**Tool best practices:**
- **Atomic** — Do one thing well
- **Typed** — Use type hints
- **Documented** — Write clear docstrings (LLM reads these!)

### Custom System Prompts
Load your own system prompts from files:

```python
agent = ReactAgent(
    tools=[...],
    prompt_file="path/to/custom_prompt.txt"
)
```

Supports `.txt`, `.md`, `.prompt` extensions. Falls back to defaults if missing.

## Documentation

- **[Tool Creation Guide](documentation/modules/tools.md)** — Detailed patterns and best practices
- **[Architecture Diagrams](documentation/architecture/)** — System design and execution flow
- **[API Reference](documentation/modules/tools_one_pager.md)** — Quick reference for all APIs

## Project Status

**BETA** — Actively developed and production-ready. Breaking changes possible until v1.0.

**Questions?** [Open an issue](https://github.com/alchemiststudiosDOTai/tinyAgent/issues)

## License

**Business Source License 1.1**

Free for:
- Individuals
- Small businesses (< $1M annual revenue)

Larger organizations: Please contact [info@alchemiststudios.ai](mailto:info@alchemiststudios.ai)

---

Made by [@tunahorse21](https://x.com/tunahorse21) at [alchemiststudios.ai](https://alchemiststudios.ai)
