# TinyAgent Setup and Example Testing Debug Session

**Date**: 2025-07-01
**Task**: Test tinyagent library examples and fix setup issues

## Issues Found and Fixed

### 1. Import Path Issues
- **Problem**: `__init__.py` was importing from `.tool` instead of `.tools`
- **Solution**: Updated import to `from .tools import tool, get_registry, freeze_registry`

### 2. Missing Prompt Templates
- **Problem**: `prompt.py` was empty but `agent.py` expected `BAD_JSON` and `SYSTEM` constants
- **Solution**: Implemented the required prompt templates:
  ```python
  SYSTEM = """You are a helpful assistant that can use tools to answer questions...
  Available tools:
  {tools}
  ..."""

  BAD_JSON = """Your previous response was not valid JSON. Please try again..."""
  ```

### 3. Tool Object vs Function Handling
- **Problem**: The `@tool` decorator returns the original function, but `ReactAgent` expects Tool objects with `.name` attribute
- **Solution**: Modified `ReactAgent.__post_init__` to handle both Tool objects and functions by looking them up in the registry

### 4. Dataclass Slots Issue
- **Problem**: Using `slots=True` with dataclass caused AttributeError when setting `_tool_map`
- **Solution**: Removed `slots=True` from the dataclass decorator

### 5. OpenAI API v1 Compatibility
- **Problem**: Code was using deprecated `openai.ChatCompletion.create()` API
- **Solution**: Updated to use new OpenAI v1 API:
  - Changed import to `from openai import OpenAI`
  - Created client instance: `self.client = OpenAI(api_key=api_key, base_url=base_url)`
  - Updated chat method to use `self.client.chat.completions.create()`

### 6. Tool Response Message Format
- **Problem**: Using `{"role": "tool", ...}` caused error with OpenRouter
- **Solution**: Changed to `{"role": "user", "content": f"Tool '{name}' returned: {result}"}`

## Setup Details

- **Environment**: Python 3.10.12 virtual environment
- **API**: OpenRouter with OpenAI-compatible interface
- **Configuration**: Created `.env` file with:
  ```
  OPENAI_API_KEY=sk-or-v1-...
  OPENAI_BASE_URL=https://openrouter.ai/api/v1
  ```

## Test Results

Successfully ran `examples/calc_demo.py`:
- Question: "What is 12 times 5, then divided by 3?"
- Result: 20.0 ✓

## Key Files Modified

1. `/tinyagent/__init__.py` - Fixed import paths
2. `/tinyagent/prompt.py` - Added SYSTEM and BAD_JSON prompts
3. `/tinyagent/agent.py` - Multiple fixes for API compatibility and tool handling

## Lessons Learned

- When using slots in dataclasses, all instance attributes must be declared
- OpenAI v1 API requires different client initialization and method calls
- OpenRouter doesn't support the "tool" message role; use "user" role instead
- Tool decorators may return the original function while the agent expects Tool objects
