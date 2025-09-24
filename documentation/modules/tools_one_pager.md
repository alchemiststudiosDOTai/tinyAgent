# Tools: One-Page Guide

This page explains how TinyAgent tools work, how to create them, and how the agent uses them — in one page.

## What Is a Tool?
- A tool is a regular Python function decorated with `@tool` from `tinyagent.tools`.
- The decorator auto-registers the function into a global registry with its name, docstring, and typed signature.
- The agent uses the registry metadata to describe tools to the LLM and to validate arguments before execution.

## How The Agent Uses Tools
- The agent renders a system prompt that lists all available tools as: `- name: description | args=(signature)`.
- The LLM replies in strict JSON. Two valid shapes:
  - Tool call: `{"scratchpad": "thinking…", "tool": "name", "arguments": {"param": "value"}}`
  - Final answer: `{"scratchpad": "summary…", "answer": "…"}`
- The agent validates `arguments` against the tool’s Python signature, executes the function, truncates long outputs to 500 chars, and feeds the observation back to the LLM.

## Quick Start
```python
from tinyagent import ReactAgent
from tinyagent.tools import tool

@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b

@tool
def divide(a: float, b: float) -> float:
    """Divide a by b."""
    if b == 0:
        raise ValueError("Division by zero")
    return a / b

agent = ReactAgent(tools=[multiply, divide])
print(agent.run("What is 12 * 5, then / 3?"))  # → 20
```

## Authoring Tools (Best Practices)
- Use clear names and short, action-oriented docstrings — the LLM relies on them.
- Type everything. Signatures are used for argument validation.
- Keep tools small, deterministic, and side-effect aware. Return values, don’t print.
- Raise exceptions for hard failures; the agent surfaces them as errors in observations.
- Keep outputs concise; the agent truncates to 500 chars for prompt hygiene.

### Common Patterns
```python
from tinyagent.tools import tool

# Simple data transform
@tool
def word_count(text: str) -> int:
    """Count words in text."""
    return len(text.split())

# Multi-arg with validation
@tool
def create_user(name: str, email: str, age: int) -> str:
    """Create a user after basic validation."""
    if "@" not in email:
        raise ValueError("Invalid email")
    if not (0 <= age <= 150):
        raise ValueError("Invalid age")
    return f"Created: {name} <{email}> ({age})"

# Filesystem interaction
@tool
def read_file(path: str) -> str:
    """Return file contents."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
```

## Passing Tools To The Agent
- Pass `@tool`-decorated functions directly: `ReactAgent(tools=[my_tool, other_tool])`.
- Internally, the agent resolves these via the global registry and uses their metadata.
- Advanced: you can pass `Tool` objects from `tinyagent.tools.get_registry()` if needed.

## Error Handling & Validation
- The agent binds `arguments` to the Python signature; mismatches return `ArgError`.
- Exceptions inside tools are caught and returned as `ToolError` observations.
- Prefer explicit failures over silent fallbacks — fail fast, fail loud.

## Testing Your Tools
- Start with a golden baseline test for each tool’s core behavior.
- Add agent-level tests only where the interaction matters (e.g., argument validation).
- Run tests with `pytest -q` (see `tests/api_test/` for examples).

## Environment & Models
- Configure API via env vars: `OPENAI_API_KEY` and optionally `OPENAI_BASE_URL` (OpenRouter compatible).
- Select a model at agent construction: `ReactAgent(..., model="gpt-4o-mini")` (default) or any OpenAI-compatible model.

## When To Create A New Tool
- You need capability not expressible in prompt engineering alone.
- The action is reusable, has clear inputs/outputs, and benefits from typing.
- The operation should be auditable in logs as a discrete step.

That’s it — decorate, type, document, and plug into `ReactAgent`.
