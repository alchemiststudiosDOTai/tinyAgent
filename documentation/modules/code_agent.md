# TinyCodeAgent Documentation

The `TinyCodeAgent` is a Python-executing ReAct agent with sandboxed code execution capabilities.

## Overview

TinyCodeAgent extends the ReAct pattern by allowing the LLM to generate and execute Python code in a secure environment. It combines the reasoning capabilities of LLMs with the precision of programmatic execution.

## Key Features

- Secure Python code execution sandbox
- Integration with registered tools as globals
- Controlled import system
- Final answer detection mechanism
- OpenAI-compatible API integration

## Usage

```python
from tinyagent import TinyCodeAgent, tool

@tool
def get_weather(city: str) -> dict:
    """Get weather information for a city."""
    return {"temp": 72, "condition": "sunny"}

# Initialize agent with tools
agent = TinyCodeAgent(tools=[get_weather])

# Run agent with a task
result = agent.run("What's the weather in New York?")
```

## Configuration

The TinyCodeAgent can be configured with several parameters:

- `tools`: Sequence of Tool objects or @tool decorated functions
- `model`: Model name (OpenAI format). Default "gpt-4o-mini"
- `api_key`: Optional OpenAI key; falls back to OPENAI_API_KEY env var
- `extra_imports`: Additional modules to allow in Python code
- `system_suffix`: Optional text to append to system prompt

## Execution Flow

1. System prompt is generated with available tools
2. User task is sent to LLM
3. Response is parsed for Python code blocks
4. Code is executed in sandboxed environment
5. If `final_answer()` called, return result
6. Otherwise, continue with observation
7. Repeat until final answer or step limit

## Security

The Python execution environment is secured through:

- Restricted built-in functions
- Controlled import system
- Standard output capture
- Execution step limiting
- Namespace isolation

## API Reference

### TinyCodeAgent class

#### `__init__(self, tools, model="gpt-4o-mini", api_key=None, extra_imports=(), system_suffix="")`
Initialize the TinyCodeAgent.

Parameters:
- `tools`: Sequence of Tool objects or @tool decorated functions
- `model`: Model name (OpenAI or OpenRouter format)
- `api_key`: Optional OpenAI key
- `extra_imports`: Additional modules to allow in Python code
- `system_suffix`: Optional text to append to system prompt

#### `run(self, task, *, max_steps=6, verbose=False)`
Execute the Python-based ReAct loop.

Parameters:
- `task`: The task/question to solve
- `max_steps`: Maximum number of reasoning steps
- `verbose`: If True, print detailed logs

Returns:
- Final answer string

### PythonExecutor class

#### `__init__(self, extra_imports=None)`
Initialize the Python executor.

Parameters:
- `extra_imports`: Set of module names allowed to be imported

#### `run(self, code)`
Execute Python code in sandboxed environment.

Parameters:
- `code`: Python code to execute

Returns:
- tuple[str, bool]: (output/result, is_final_answer)

## Constants

- `MAX_STEPS`: Default maximum steps (6)
- `MAX_OUTPUT_LENGTH`: Maximum output length (2000)
