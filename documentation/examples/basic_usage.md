# Basic Usage Examples

This document provides examples of how to use TinyAgent in common scenarios.

## Simple ReactAgent Example

```python
from tinyagent import ReactAgent, tool

@tool
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

# Create agent with tools
agent = ReactAgent(tools=[add_numbers])

# Ask a question
result = agent.run("What is 5 plus 3?")
print(result)  # Output: 8
```

## Web Search Example

```python
import os
from tinyagent import ReactAgent
from tinyagent.base_tools import web_search

# Set API key
os.environ["BRAVE_SEARCH_API_KEY"] = "your-api-key"

# Create agent with web search
agent = ReactAgent(tools=[web_search])

# Search the web
result = agent.run("What is the capital of France?")
print(result)
```

## TinyCodeAgent Example

```python
from tinyagent import TinyCodeAgent, tool

@tool
def get_stock_price(symbol: str) -> float:
    """Get the current stock price for a symbol."""
    # In a real implementation, this would call a financial API
    return 150.0

# Create code agent
agent = TinyCodeAgent(tools=[get_stock_price])

# Task requiring code execution
result = agent.run("Calculate the total value of 10 shares of AAPL")
print(result)
```

## Custom Model Configuration

```python
from tinyagent import ReactAgent, tool

@tool
def multiply(x: float, y: float) -> float:
    """Multiply two numbers."""
    return x * y

# Use a different model
agent = ReactAgent(
    tools=[multiply],
    model="gpt-4",
    api_key="your-api-key"
)

result = agent.run("What is 12.5 times 8?")
print(result)
```

## Verbose Mode for Debugging

```python
from tinyagent import ReactAgent, tool

@tool
def calculator(expression: str) -> float:
    """Evaluate a mathematical expression."""
    return eval(expression)

agent = ReactAgent(tools=[calculator])

# Enable verbose mode to see execution steps
result = agent.run(
    "Calculate (2 + 3) * 4",
    verbose=True
)
```

## Error Handling

```python
from tinyagent import ReactAgent, tool
from tinyagent.agent import StepLimitReached

@tool
def risky_operation(value: int) -> int:
    """An operation that might fail."""
    if value < 0:
        raise ValueError("Negative values not allowed")
    return value * 2

agent = ReactAgent(tools=[risky_operation])

try:
    result = agent.run("Process value -5")
except StepLimitReached as e:
    print(f"Agent exceeded step limit: {e}")
```

## Using Tool Objects Directly

```python
from tinyagent import ReactAgent
from tinyagent.tools import get_registry, Tool

# Get tool from registry
registry = get_registry()
add_tool = registry["add_numbers"]  # Assuming @tool decorated function

# Use Tool object directly
agent = ReactAgent(tools=[add_tool])
result = agent.run("Add 10 and 20")
```

## Environment Configuration

```python
import os
from tinyagent import ReactAgent, tool

# Set environment variables
os.environ["OPENAI_API_KEY"] = "your-openai-key"
os.environ["OPENAI_BASE_URL"] = "https://custom-api/v1"  # For custom endpoints

@tool
def echo(text: str) -> str:
    """Echo the provided text."""
    return text

agent = ReactAgent(tools=[echo])
result = agent.run("Echo 'Hello World'")
```

## Running with Custom Step Limits

```python
from tinyagent import ReactAgent, tool

@tool
def increment(value: int) -> int:
    """Increment a value by 1."""
    return value + 1

agent = ReactAgent(tools=[increment])

# Set custom step limit
result = agent.run(
    "Increment 5 three times",
    max_steps=5
)
```

These examples demonstrate the core functionality of TinyAgent. For more advanced usage, see the advanced examples documentation.
