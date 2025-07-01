# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core Architecture

TinyAgent implements a minimal ReAct (Reasoning + Acting) agent framework with three core components:

1. **ReactAgent** (`agent.py`) - Orchestrates the ReAct loop, handling tool calls and responses
2. **Tool Registry** (`tools.py`) - Global registry with `@tool` decorator for automatic function registration
3. **Prompts** (`prompt.py`) - System and error prompt templates

Key relationships:
- Functions decorated with `@tool` are automatically registered and available to agents
- ReactAgent accepts both raw functions and Tool objects
- The agent communicates via JSON for structured tool calling

## Development Commands

```bash
# Setup development environment
python3 -m venv venv
source venv/bin/activate
pip install -e .
pip install pytest pre-commit

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/test_agent.py -v

# Run specific test
pytest tests/test_agent.py::TestReactAgent::test_agent_initialization_with_function_tools -v

# Run linting and formatting
ruff check . --fix
ruff format .

# Run all pre-commit checks
pre-commit run --all-files

# Run examples (requires OPENAI_API_KEY)
python examples/calc_demo.py
```

## Critical Implementation Details

### Tool Registration Pattern
The `@tool` decorator returns the original function but registers it in a global registry. When passing tools to ReactAgent:
- Raw functions are looked up in the registry during `__post_init__`
- Tool objects are used directly
- Invalid tools raise ValueError

### API Configuration
- Uses OpenAI v1 API (`from openai import OpenAI`)
- Supports OpenRouter via `OPENAI_BASE_URL` environment variable
- API key sourced from: constructor argument > `OPENAI_API_KEY` env var

### Message Format
The agent uses "user" role for tool responses (not "tool" role) to maintain compatibility with OpenRouter:
```python
{"role": "user", "content": f"Tool '{name}' returned: {result}"}
```

### Testing Approach
Tests use mocked OpenAI responses to verify agent behavior without API calls. Key patterns:
- Registry cleanup in setup/teardown
- Mock response chains for multi-step interactions
- Temperature adjustment verification for retry logic

## Project-Specific Configurations

- **Ruff**: Line length 100, Python 3.10+, configured in `pyproject.toml`
- **Pre-commit**: Runs ruff (lint + format) and pytest on `test_agent.py`
- **Environment**: Uses `.env` file for API configuration (OpenRouter setup)

## Common Issues and Solutions

1. **Import errors**: Check that imports use `tinyagent.tools` (not `.tool`) and `tinyagent.agent` (not `.react`)
2. **Tool registration**: Ensure `@tool` decorated functions are imported before creating agents
3. **API compatibility**: Message format must use "user" role for tool responses with OpenRouter