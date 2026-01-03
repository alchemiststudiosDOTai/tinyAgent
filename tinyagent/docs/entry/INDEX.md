---
title: Entry Points Documentation Index
path: docs/entry/
type: directory
depth: 0
description: Index of all tinyAgent entry points and public APIs
exports: []
seams: []
---

# tinyAgent Entry Points Documentation

Comprehensive documentation of all public APIs, main classes, and interfaces in the tinyAgent framework.

## Quick Reference

### Core Entry Points
- **[tinyagent Root Package](tinyagent-root.md)** - Main package with all public exports
- **[ReactAgent](react-agent.md)** - JSON tool-calling agent
- **[TinyCodeAgent](tinycode-agent.md)** - Python code execution agent
- **[BaseAgent](base-agent.md)** - Abstract base class for all agents

### Tool System
- **[tool Decorator](tool-decorator.md)** - Create tools from functions
- **[ToolCallingMode](tool-calling-mode.md)** - Tool calling adapter modes
- **[Built-in Tools](built-in-tools.md)** - Pre-built tools (web search, planning, etc.)
- **[Tool Validation](validation.md)** - Static analysis for tool classes

### Memory & State
- **[Memory System](memory-system.md)** - Conversation history and working memory
- **[Signals](signals.md)** - Cognitive primitives for reasoning state

### Execution
- **[Execution System](execution-system.md)** - Code execution backends and limits

### Configuration
- **[Prompt System](prompt-system.md)** - System prompt templates and loading

### Types & Errors
- **[Types and Exceptions](types-and-exceptions.md)** - Core types and error handling

## By Category

### Agents

| Class | File | Description |
|-------|------|-------------|
| `ReactAgent` | [react-agent.md](react-agent.md) | JSON tool-calling agent |
| `TinyCodeAgent` | [tinycode-agent.md](tinycode-agent.md) | Python code execution agent |
| `BaseAgent` | [base-agent.md](base-agent.md) | Abstract base class |

### Tools & Tooling

| Component | File | Description |
|-----------|------|-------------|
| `@tool` | [tool-decorator.md](tool-decorator.md) | Decorator for creating tools |
| `ToolCallingMode` | [tool-calling-mode.md](tool-calling-mode.md) | Tool calling modes |
| `web_search` | [built-in-tools.md](built-in-tools.md) | Web search tool |
| `web_browse` | [built-in-tools.md](built-in-tools.md) | Web browsing tool |
| Planning tools | [built-in-tools.md](built-in-tools.md) | Plan management |
| `validate_tool_class` | [validation.md](validation.md) | Tool class validator |

### Memory System

| Component | File | Description |
|-----------|------|-------------|
| `AgentMemory` | [memory-system.md](memory-system.md) | Working memory/scratchpad |
| `MemoryManager` | [memory-system.md](memory-system.md) | Conversation history |
| `Step` classes | [memory-system.md](memory-system.md) | Memory step types |
| Pruning strategies | [memory-system.md](memory-system.md) | Memory pruning |

### Execution

| Component | File | Description |
|-----------|------|-------------|
| `Executor` | [execution-system.md](execution-system.md) | Execution protocol |
| `LocalExecutor` | [execution-system.md](execution-system.md) | In-process executor |
| `ExecutionLimits` | [execution-system.md](execution-system.md) | Resource limits |
| `ExecutionResult` | [execution-system.md](execution-system.md) | Execution outcome |
| `ExecutionTimeout` | [execution-system.md](execution-system.md) | Timeout exception |

### Signals

| Component | File | Description |
|-----------|------|-------------|
| `uncertain` | [signals.md](signals.md) | Signal uncertainty |
| `explore` | [signals.md](signals.md) | Signal exploration |
| `commit` | [signals.md](signals.md) | Signal confidence |

### Prompts

| Component | File | Description |
|-----------|------|-------------|
| `SYSTEM` | [prompt-system.md](prompt-system.md) | ReAct system prompt |
| `CODE_SYSTEM` | [prompt-system.md](prompt-system.md) | Code execution prompt |
| `BAD_JSON` | [prompt-system.md](prompt-system.md) | JSON retry prompt |
| Prompt loaders | [prompt-system.md](prompt-system.md) | File loading utilities |

### Types & Exceptions

| Component | File | Description |
|-----------|------|-------------|
| `RunResult` | [types-and-exceptions.md](types-and-exceptions.md) | Execution result |
| `FinalAnswer` | [types-and-exceptions.md](types-and-exceptions.md) | Final answer with metadata |
| `Finalizer` | [types-and-exceptions.md](types-and-exceptions.md) | Final answer manager |
| `StepLimitReached` | [types-and-exceptions.md](types-and-exceptions.md) | Max steps exception |
| `MultipleFinalAnswers` | [types-and-exceptions.md](types-and-exceptions.md) | Idempotency exception |
| `InvalidFinalAnswer` | [types-and-exceptions.md](types-and-exceptions.md) | Validation exception |
| `ToolDefinitionError` | [types-and-exceptions.md](types-and-exceptions.md) | Tool decorator error |
| `ToolValidationError` | [types-and-exceptions.md](types-and-exceptions.md) | Tool validation error |

## By Use Case

### Getting Started

1. **Install**: `pip install tinyagent`
2. **Import**: `import tinyagent`
3. **Choose Agent**: `ReactAgent` or `TinyCodeAgent`
4. **Run**: `agent.run_sync("your task")`

See [tinyagent Root Package](tinyagent-root.md) for complete API surface.

### Tool Calling

Use **ReactAgent** with tools:

```python
from tinyagent import ReactAgent, tool

@tool
def my_function(param: str) -> str:
    """Do something."""
    return f"Result: {param}"

agent = ReactAgent(
    model="gpt-4o-mini",
    tools=[my_function]
)

result = agent.run_sync("Use my_function with 'hello'")
```

See [ReactAgent](react-agent.md) and [tool Decorator](tool-decorator.md).

### Code Execution

Use **TinyCodeAgent** for Python tasks:

```python
from tinyagent import TinyCodeAgent, TrustLevel

agent = TinyCodeAgent(
    model="gpt-4o",
    trust_level=TrustLevel.ISOLATED
)

result = agent.run_sync(
    "Calculate the mean of [1, 2, 3, 4, 5]"
)
```

See [TinyCodeAgent](tinycode-agent.md) and [Execution System](execution-system.md).

### Custom Tools

Create tools with the `@tool` decorator:

```python
from tinyagent import tool

@tool
def search(query: str, max_results: int = 5) -> str:
    """Search and return results."""
    return f"Results for: {query}"
```

See [tool Decorator](tool-decorator.md) and [Tool Validation](validation.md).

### Memory Management

Manage conversation history:

```python
from tinyagent import MemoryManager, keep_last_n_steps

memory = MemoryManager(
    system_prompt="You are helpful.",
    enable_pruning=True
)

agent = ReactAgent(memory_manager=memory)
```

See [Memory System](memory-system.md).

### Custom Prompts

Use custom system prompts:

```python
agent = ReactAgent(
    prompt_file="prompts/custom.md"
)
```

See [Prompt System](prompt-system.md).

## File Structure

```
docs/entry/
├── INDEX.md                  # This file
├── tinyagent-root.md         # Main package exports
├── react-agent.md            # ReactAgent documentation
├── tinycode-agent.md         # TinyCodeAgent documentation
├── base-agent.md             # BaseAgent documentation
├── tool-decorator.md         # @tool decorator
├── tool-calling-mode.md      # ToolCallingMode enum
├── built-in-tools.md         # Pre-built tools
├── validation.md             # Tool validation
├── memory-system.md          # Memory management
├── signals.md                # Cognitive primitives
├── execution-system.md       # Code execution
├── prompt-system.md          # Prompt templates
└── types-and-exceptions.md   # Core types and errors
```

## Conventions

### Frontmatter

Each file includes required frontmatter:

```yaml
---
title: Human-readable name
path: relative/path/from/root
type: file
depth: 0-N
description: One-line purpose summary
exports: [list, of, key, exports]
seams: [E]
---
```

### Fields

- **title**: Display name
- **path**: Relative path from tinyagent root
- **type**: "file" or "directory"
- **depth**: Nesting level (0 = root, 1 = direct child, etc.)
- **description**: Single-line summary
- **exports**: List of key exports (classes, functions, constants)
- **seams**: Extension points ("E" for extensibility)

## Related Documentation

- **Architecture**: See `../architecture/` for design docs
- **Tutorials**: See `../tutorials/` for step-by-step guides
- **Examples**: See `../examples/` for code samples
- **API Reference**: See individual module documentation

## Contributing

When adding new entry points:

1. **Document public APIs** in appropriate file
2. **Use required frontmatter** with exports field
3. **Include examples** for all public methods
4. **Add to index** (this file)
5. **Link from related docs**

## Support

- **Issues**: Report bugs via GitHub issues
- **Questions**: Use GitHub discussions
- **Contributions**: Pull requests welcome

---

*Documentation generated for tinyAgent framework*
