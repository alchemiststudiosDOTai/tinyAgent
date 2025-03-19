# Turn Any Function Into an Agent! 🤖

This framework makes it super easy to turn any Python function into an AI agent. Here's how:

## Basic Example

```python
from core.factory import AgentFactory

# Create the factory
factory = AgentFactory.get_instance()

# Turn a function into an agent tool
@factory.create_tool(
    name="greet",
    description="Says hello to someone"
)
def greet(name: str):
    return f"Hello {name}!"

# Create an agent with this tool
agent = factory.create_agent(tools=[greet])
```

## Features

- **Rate Limiting**: Built-in protection against too many API calls
- **Parameter Validation**: Automatic type checking for your function parameters
- **Error Handling**: Smart error management built-in

## Calculator Example

Here's a more complete example showing a calculator tool:

```python
from core.tool import Tool
from core.agent import Agent

# Create a calculator tool
calculator_tool = Tool(
    name="calculator",
    description="Perform basic arithmetic operations",
    parameters={
        "operation": "string",  # add, subtract, multiply, divide
        "a": "integer",
        "b": "integer"
    },
    func=calculate
)

# Create an agent with the calculator
agent = Agent(tools=[calculator_tool])

# Use it!
result = agent.run("Calculate 5 + 3")
```

## Two Ways to Create Tools

1. **Using Decorators** (easiest):
   ```python
   @factory.create_tool(name="mytool", description="does something cool")
   def my_function():
       pass
   ```

2. **Direct Tool Creation**:
   ```python
   tool = Tool(name="mytool", description="does something cool", func=my_function)
   ```

Choose whichever style works best for your needs!
