# Turn Any Function Into an Agent Tool! 🤖

tinyAgent makes it SIMPLE to turn any Python function into an AI agent tool—just add the `@tool` decorator. No boilerplate, no complex setup.

## Minimal Example

```python
from tinyagent.decorators import tool
from tinyagent.agent import tiny_agent

@tool
def greet_person(name: str) -> str:
    """Return a friendly greeting."""
    return f"Hello, {name}!"

agent = tiny_agent(tools=[greet_person])
print(agent.run("greet Alice"))  # → Hello, Alice!
```

## Calculator Example

```python
from tinyagent.decorators import tool
from tinyagent.agent import tiny_agent

@tool
def calculate_sum(a: int, b: int) -> int:
    """Return the sum of two integers."""
    return a + b

agent = tiny_agent(tools=[calculate_sum])
print(agent.run("calculate the sum of 5 and 3"))  # → 8
```

## How the `@tool` Decorator Works

- Registers your function as a tool, making it discoverable by agents.
- Extracts the function's name, signature, and docstring for use in tool metadata.
- Optionally allows you to override the tool's name and description.

```python
@tool(name="greet", description="Say hello to someone by name")
def greet_person(name: str) -> str:
    return f"Hello, {name}!"
```

If you don't specify a name or description, the function name and docstring are used.

## Argument Mapping & Type Validation

- The agent uses LLM-powered parsing to map user queries to function arguments.
- Type hints are enforced: if the user provides an invalid type, the agent will attempt to correct or ask for clarification.
- Example: If your function expects `a: int`, and the user says "add five and three," the agent will convert "five" and "three" to integers.

```python
@tool
def calculate_sum(a: int, b: int) -> int:
    """Return the sum of two integers."""
    return a + b

agent = tiny_agent(tools=[calculate_sum])
print(agent.run("add five and three"))  # → 8
```

## Error Handling

- If the function raises an error, the agent will catch it and return a helpful message.
- If arguments are missing or invalid, the agent will prompt for clarification.

```python
@tool
def divide(a: float, b: float) -> float:
    """Divide a by b."""
    return a / b

agent = tiny_agent(tools=[divide])
print(agent.run("divide 10 by 0"))  # → Handles ZeroDivisionError gracefully
```

## Customizing Tool Metadata

- You can provide a custom name and description:

```python
@tool(name="weather", description="Get the weather for a city")
def get_weather(city: str) -> str:
    return f"Weather for {city} is sunny."
```

- If not provided, the function name and docstring are used.

## How Agents Use Tools

- Tools are passed to the agent via the `tools` argument.
- The agent will automatically select and call the correct tool based on the user's query.
- You can provide multiple tools; the agent will choose the best match.

```python
@tool
def greet(name: str) -> str:
    return f"Hello, {name}!"

@tool
def farewell(name: str) -> str:
    return f"Goodbye, {name}!"

agent = tiny_agent(tools=[greet, farewell])
print(agent.run("say goodbye to Bob"))  # → Goodbye, Bob!
```

## Advanced Usage

### Complex Parameter Types

You can use lists, enums, and more as arguments:

```python
from typing import List

@tool(description="Calculate the average of a list of numbers")
def average(numbers: List[float]) -> float:
    """Return the average of a list of numbers."""
    return sum(numbers) / len(numbers)

agent = tiny_agent(tools=[average])
print(agent.run("What is the average of 3, 5, and 7?"))  # → 5.0
```

### Chaining Tools (tiny_chain)

For multi-step workflows, use with `tiny_chain`:

```python
from tinyagent.factory.tiny_chain import tiny_chain
from tinyagent.tools.duckduckgo_search import get_tool as search_tool
from tinyagent.tools.custom_text_browser import get_tool as browser_tool
from tinyagent.decorators import tool
from tinyagent.agent import get_llm

@tool(name="summarize", description="Summarize input text with the LLM")
def summarize(text: str) -> str:
    prompt = f"Summarize the following text:\n\n{text}\n\nSummary:"
    return get_llm()(prompt).strip()

chain = tiny_chain.get_instance(
    tools=[search_tool(), browser_tool(), summarize._tool]
)
task_id = chain.submit_task(
    "Find current US import tariffs and visit official trade websites for details"
)
print(chain.get_task_status(task_id).result)
```

## Best Practices

- Always provide type hints and docstrings for your tool functions.
- Use descriptive names and docstrings to help the agent understand the tool's purpose.
- Test your tools interactively to ensure the agent can map queries correctly.

## Debugging & Introspection

- You can inspect registered tools via `agent.tools` to see their metadata.
- Use logging or print statements in your tool functions for debugging.

## Philosophy

Any function → tool → agent. No boilerplate, just decorate and go.

For advanced usage, parameter validation, and error handling, see [documentation/rest.md](rest.md).
