# The Factory Pattern in tinyAgent 🏭

## Simple Explanation

The Factory in tinyAgent works like a central tool registry:

1. **Tools are registered once** in the factory
2. **Multiple agents can use these tools** without duplicating code
3. **Resources are managed centrally** (like limiting how often tools can be used)

```python
# The simple one-liner to create an agent with a tool
agent = AgentFactory.get_instance().create_agent(tools=[my_function])
```

Think of the factory as a smart tool manager that:

- Keeps track of all your available tools
- Controls how often tools can be used
- Makes sure tools are used correctly
- Lets many agents share the same tools

## Technical Details

### Core Concepts

The `AgentFactory` class implements the Singleton pattern to provide a central registry for tools and agent creation. It serves several important purposes:

1. **Centralized Tool Management**:

   - Tools are registered once with `factory.register_tool(tool)`
   - All agents created by the factory have access to registered tools
   - Common tools are shared across the application

2. **Resource Control**:

   - Implements rate limiting based on configuration
   - Tracks call counts for each tool
   - Prevents excessive API usage

3. **Standardization**:

   - Ensures consistent tool format and parameter validation
   - Manages tool lifecycle and execution flow
   - Provides uniform error handling

4. **Orchestration**:
   - Facilitates multi-agent coordination (see [orchestration.md](orchestration.md))
   - Enables creation of specialized agents for specific tasks
   - Supports dynamic tool creation based on requirements

### Usage Patterns

#### Basic Tool Registration

```python
from tinyagent.factory.agent_factory import AgentFactory
from tinyagent.decorators import tool

# Get factory instance
factory = AgentFactory.get_instance()

# Define tool with decorator
@tool
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two integers."""
    return a + b

# Register with factory
factory.register_tool(calculate_sum._tool)

# Create agent with factory tools
agent = factory.create_agent()
```

#### Direct Agent Creation with Tools

```python
# One-line agent creation with tool
agent = AgentFactory.get_instance().create_agent(tools=[calculate_sum])

# Now the agent can use the tool
result = agent.run("calculate the sum of 5 and 3")  # Returns 8
```

### Advanced Features

#### Rate Limiting

The factory controls how often tools can be called:

```python
# Tool with custom rate limit (5 calls max)
@tool(rate_limit=5)
def limited_api_call():
    # API call that should be limited
    pass

# Global rate limits in config.yml
rate_limits:
  global: 30  # Default for all tools
  tools:
    limited_api_call: 5  # Tool-specific limit
```

#### Dynamic Tool Creation

For advanced use cases, the `DynamicAgentFactory` extends `AgentFactory` with the ability to create tools on-the-fly:

```python
from tinyagent.factory.dynamic_agent_factory import DynamicAgentFactory

# Get dynamic factory
dynamic_factory = DynamicAgentFactory.get_instance()

# Create specialized agent based on task description
agent_result = dynamic_factory.create_agent_from_requirement(
    "I need an agent that can analyze financial data"
)

if agent_result["success"]:
    specialized_agent = agent_result["agent"]
```

#### Inherited Tool Access

All agents created by the factory inherit access to factory-registered tools:

```python
# Register global tools
factory.register_tool(tool1)
factory.register_tool(tool2)

# All these agents can use tool1 and tool2
agent1 = factory.create_agent()
agent2 = factory.create_agent(tools=[custom_tool])  # Has tool1, tool2, AND custom_tool
```

### Implementation Details

The Factory implements:

1. **Singleton Pattern**: `get_instance()` ensures only one factory exists
2. **Tool Registry**: `_tools` dictionary maps tool names to instances
3. **Usage Tracking**: `_call_counts` tracks how often each tool is called
4. **Configuration Integration**: Uses `config.yml` for rate limits and options

### Related Concepts

For more information on related topics, see:

- [Agents as Functions](agentsarefunction.md) - How tools relate to functions
- [Orchestration](orchestration.md) - How multiple agents work together
- [Agents](agents.md) - General agent capabilities

## When to Use the Factory

**Use the factory when**:

- Building applications with multiple agents
- Sharing tools across different components
- Needing centralized resource management
- Implementing rate limiting or usage tracking
- Creating specialized agents dynamically

**For simple scripts**, the one-liner is sufficient:

```python
agent = AgentFactory.get_instance().create_agent(tools=[my_tool])
```

```

You can save this content as `documentation/FACTORY.md`. The file provides a simple explanation of the factory pattern followed by more technical details, covering the core concepts, usage patterns, advanced features, and implementation details.
```
