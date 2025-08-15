# ReactAgent Documentation

The `ReactAgent` is a lightweight implementation of the ReAct (Reason + Act) pattern with JSON-based tool calling.

## Overview

ReactAgent provides a minimal, typed implementation of the ReAct loop that works with any OpenAI-compatible API. It uses JSON-formatted responses to determine when to call tools and when to provide final answers.

## Key Features

- JSON-based tool calling interface
- Configurable step limits and error handling
- Support for multiple tool types
- Verbose logging for debugging
- OpenAI-compatible API integration

## Usage

```python
from tinyagent import ReactAgent, tool

@tool
def calculator(expression: str) -> float:
    """Evaluate a mathematical expression."""
    return eval(expression)

# Initialize agent with tools
agent = ReactAgent(tools=[calculator])

# Run agent with a question
result = agent.run("What is 15% of 200?")
```

## Configuration

The ReactAgent can be configured with several parameters:

- `tools`: Sequence of Tool objects or @tool decorated functions
- `model`: Model name (OpenAI format). Default "gpt-4o-mini"
- `api_key`: Optional OpenAI key; falls back to OPENAI_API_KEY env var

## Execution Flow

1. System prompt is generated with available tools
2. User question is sent to LLM
3. Response is parsed as JSON
4. If contains "tool" and "arguments", execute the tool
5. If contains "answer", return the result
6. If malformed JSON, retry with error correction
7. Continue until step limit or final answer

## Error Handling

- JSON parsing errors trigger retry with increased temperature
- Tool execution errors are returned as observations
- Step limit exceeded raises `StepLimitReached` exception
- Unknown tools return error messages

## API Reference

### ReactAgent class

#### `__init__(self, tools, model="gpt-4o-mini", api_key=None)`
Initialize the ReactAgent.

Parameters:
- `tools`: Sequence of Tool objects
- `model`: Model name (OpenAI format)
- `api_key`: Optional OpenAI key

#### `run(self, question, *, max_steps=10, verbose=False)`
Execute the ReAct loop.

Parameters:
- `question`: The question to answer
- `max_steps`: Maximum number of reasoning steps
- `verbose`: If True, print detailed execution logs

Returns:
- Final answer string

## Internal Methods

### `_chat(messages, temperature, verbose=False)`
Single LLM call with OpenAI-compatible API.

### `_try_parse_json(text)`
Parse JSON with error handling.

### `_safe_tool(name, args, verbose=False)`
Execute tool with argument validation.

## Constants

- `MAX_STEPS`: Default maximum steps (10)
- `TEMP_STEP`: Temperature increase per retry (0.2)
- `MAX_OBS_LEN`: Maximum observation length (500)
