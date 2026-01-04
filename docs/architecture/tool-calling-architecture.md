---
title: Tool Calling Architecture
path: architecture/
type: directory
depth: 0
description: Tool registration, adapters, and execution patterns
seams: [A]
---

# Tool Calling Architecture

## Overview

The tool calling system is one of the most critical components of the tinyAgent framework. It employs a sophisticated adapter-based architecture that enables agents to work seamlessly with different LLM tool-calling mechanisms while maintaining a consistent interface.

---

## Architecture Overview

### High-Level Flow

```
┌─────────────────────────────────────────────────────────┐
│                     Tool Registry                        │
│  (@tool decorator → validation → schema generation)     │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   Agent Initialization                   │
│  (Tool list → BaseAgent._tool_map[name] → Tool)         │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                 Tool Calling Adapter                     │
│  (Model-specific format → LLM request → response)       │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    Tool Execution                        │
│  (Tool lookup → argument validation → execution)        │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    Result Formatting                     │
│  (Output → message → memory update)                     │
└─────────────────────────────────────────────────────────┘
```

---

## Tool Registry

**Location:** `/Users/tuna/tinyAgent/tinyagent/core/registry.py`

### The `@tool` Decorator

```python
def tool(func: Callable) -> Tool:
    """
    Decorator to convert a function into a Tool.

    Validates:
    - Function has docstring
    - Function has type hints
    - Function signature is serializable

    Returns:
        Tool object with metadata and JSON schema
    """

    # Fail-fast validation
    _validate_function(func)

    # Generate JSON schema from signature
    schema = generate_json_schema(func)

    # Create tool object
    return Tool(
        name=func.__name__,
        func=func,
        schema=schema,
        doc=func.__doc__,
    )
```

### Validation Rules

```python
def _validate_function(func: Callable) -> None:
    """Validate function meets tool requirements"""

    # Must have docstring
    if not func.__doc__:
        raise ToolDefinitionError(
            f"Tool '{func.__name__}' must have a docstring. "
            "This is required for LLM function descriptions."
        )

    # Must have type hints
    hints = get_type_hints(func)
    if not hints:
        raise ToolDefinitionError(
            f"Tool '{func.__name__}' must have type hints. "
            "Required for schema generation and validation."
        )

    # Check return type
    if "return" not in hints:
        raise ToolDefinitionError(
            f"Tool '{func.__name__}' must have return type annotation"
        )
```

### Tool Object

```python
@dataclass
class Tool:
    """Represents a callable tool with metadata"""

    name: str                      # Function name
    func: Callable                 # Actual function
    schema: dict[str, Any]        # JSON Schema for arguments
    doc: str                      # Docstring (LLM description)

    async def run(self, **kwargs) -> Any:
        """Execute tool with argument validation"""
        # Validate arguments against schema
        # Execute function (sync or async)
        # Return result
```

### Example Tool Definition

```python
@tool
async def web_search(query: str, num_results: int = 5) -> str:
    """
    Search the web for information.

    Args:
        query: Search query string
        num_results: Number of results to return (default: 5)

    Returns:
        Formatted search results as text
    """
    results = await search_api(query, limit=num_results)
    return format_results(results)
```

**Generated Schema:**
```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Search query string"
    },
    "num_results": {
      "type": "integer",
      "description": "Number of results to return",
      "default": 5
    }
  },
  "required": ["query"]
}
```

---

## Schema Generation

**Location:** `/Users/tuna/tinyAgent/tinyagent/core/schema.py`

### Type Mapping

```python
def python_type_to_json(python_type: type) -> dict[str, Any]:
    """Map Python types to JSON Schema types"""

    mapping = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array"},
        dict: {"type": "object"},
    }

    return mapping.get(python_type, {"type": "string"})
```

### Complex Types

```python
def generate_schema_from_signature(func: Callable) -> dict[str, Any]:
    """Generate JSON Schema from function signature"""

    hints = get_type_hints(func)
    sig = signature(func)

    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        param_type = hints.get(param_name, str)

        # Get JSON type
        prop_schema = python_type_to_json(param_type)

        # Add description from docstring
        if func.__doc__:
            prop_schema["description"] = extract_param_description(
                func.__doc__,
                param_name
            )

        # Check if required
        if param.default == Parameter.empty:
            required.append(param_name)
        else:
            prop_schema["default"] = param.default

        properties[param_name] = prop_schema

    return {
        "type": "object",
        "properties": properties,
        "required": required
    }
```

---

## Tool Calling Adapters

**Location:** `/Users/tuna/tinyAgent/tinyagent/core/adapters.py`

### The Problem

Different LLMs have different tool-calling mechanisms:

| Model | Tool Calling Format |
|-------|---------------------|
| GPT-4 | Native function calling API |
| Claude 3 | Native function calling API |
| Llama 2 | Manual JSON parsing |
| Mistral | Structured JSON output |
| Local models | Text parsing |

**Without adapters:** Agent would need model-specific code for each model.

**With adapters:** Single agent works with all models transparently.

---

### Adapter Protocol

```python
class ToolCallingAdapter(Protocol):
    """Protocol for adapting agent to different LLM tool-calling mechanisms"""

    async def format_request(self, tools: list[Tool]) -> dict[str, Any]:
        """
        Format tools for LLM request.

        Returns:
            Dictionary to merge into API request body
        """
        ...

    async def extract_tool_call(
        self,
        response: Any,
        available_tools: dict[str, Tool]
    ) -> ToolCall | None:
        """
        Extract tool call from LLM response.

        Returns:
            ToolCall if found, None otherwise
        """
        ...
```

---

### NativeToolAdapter

**For:** GPT-4, Claude 3 (models with native function calling)

```python
class NativeToolAdapter:
    """Use model's native function calling API"""

    def __init__(self, tools: list[Tool]):
        self._tools = tools

    async def format_request(self) -> dict[str, Any]:
        """Format tools for OpenAI/Claude API"""
        return {
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.doc,
                        "parameters": tool.schema
                    }
                }
                for tool in self._tools
            ]
        }

    async def extract_tool_call(
        self,
        response: Any,
        available_tools: dict[str, Tool]
    ) -> ToolCall | None:
        """Extract native tool call from response"""
        message = response.choices[0].message

        # Check for tool calls
        if not message.tool_calls:
            return None

        # Extract first tool call
        call = message.tool_calls[0]
        function = call.function

        # Parse arguments
        arguments = json.loads(function.arguments)

        return ToolCall(
            id=call.id,
            name=function.name,
            arguments=arguments
        )
```

**Request Format:**
```python
{
    "messages": [...],
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web...",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"]
                }
            }
        }
    ]
}
```

**Response Format:**
```python
{
    "choices": [{
        "message": {
            "role": "assistant",
            "tool_calls": [{
                "id": "call_abc123",
                "type": "function",
                "function": {
                    "name": "web_search",
                    "arguments": '{"query": "python help"}'
                }
            }]
        }
    }]
}
```

---

### OpenAIStructuredAdapter

**For:** Models that support structured JSON output (but not native tools)

```python
class OpenAIStructuredAdapter:
    """Use structured JSON output mode for tool calls"""

    def __init__(self, tools: list[Tool]):
        self._tools = tools
        self._tool_map = {tool.name: tool for tool in tools}

    async def format_request(self) -> dict[str, Any]:
        """Format request to force JSON output"""
        # Build tool descriptions for prompt
        tool_descriptions = "\n".join([
            f"- {tool.name}: {tool.doc}"
            for tool in self._tools
        ])

        # Add tools to system prompt
        system_prompt = f"""
        Available tools:
        {tool_descriptions}

        When calling a tool, respond with JSON format:
        {{"tool": "tool_name", "arguments": {{...}}}}
        """

        return {
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system_prompt}]
        }

    async def extract_tool_call(
        self,
        response: Any,
        available_tools: dict[str, Tool]
    ) -> ToolCall | None:
        """Parse JSON tool call from response"""
        content = response.choices[0].message.content

        try:
            data = json.loads(content)

            if "tool" in data:
                return ToolCall(
                    id=None,  # No native tool call ID
                    name=data["tool"],
                    arguments=data.get("arguments", {})
                )
        except json.JSONDecodeError:
            return None
```

**Request Format:**
```python
{
    "response_format": {"type": "json_object"},
    "messages": [
        {
            "role": "system",
            "content": "Available tools:\n- web_search: Search web\n\nRespond with: {\"tool\": \"name\", \"arguments\": {...}}"
        }
    ]
}
```

**Response Format:**
```python
{
    "choices": [{
        "message": {
            "content": '{"tool": "web_search", "arguments": {"query": "python help"}}'
        }
    }]
}
```

---

### ValidatedAdapter

**For:** Adding runtime validation to any adapter

```python
class ValidatedAdapter:
    """Wrap any adapter with Pydantic validation"""

    def __init__(self, base_adapter: ToolCallingAdapter):
        self._base = base_adapter

    async def format_request(self, tools: list[Tool]) -> dict[str, Any]:
        """Passthrough to base adapter"""
        return await self._base.format_request(tools)

    async def extract_tool_call(
        self,
        response: Any,
        available_tools: dict[str, Tool]
    ) -> ToolCall | None:
        """Extract and validate tool call"""
        call = await self._base.extract_tool_call(response, available_tools)

        if call:
            # Validate against tool schema
            tool = available_tools[call.name]
            validated = validate_arguments(call.arguments, tool.schema)
            call.arguments = validated

        return call
```

---

### Adapter Factory

```python
def get_adapter(
    model: str,
    tools: list[Tool],
    mode: str = "auto"
) -> ToolCallingAdapter:
    """
    Factory for selecting appropriate adapter.

    Modes:
    - auto: Automatically detect based on model
    - native: Force native tool calling
    - structured: Force structured JSON
    - validated: Force with validation
    """

    if mode == "validated":
        base = get_adapter(model, tools, mode="auto")
        return ValidatedAdapter(base)

    if mode == "native" or supports_native_tools(model):
        return NativeToolAdapter(tools)

    elif mode == "structured" or supports_structured_output(model):
        return OpenAIStructuredAdapter(tools)

    else:
        # Fallback to structured with validation
        return ValidatedAdapter(OpenAIStructuredAdapter(tools))
```

---

## Tool Execution

### Execution Flow

```python
# 1. Extract tool call from LLM response
tool_call = await adapter.extract_tool_call(response, self._tool_map)

# 2. Look up tool
tool = self._tool_map[tool_call.name]

# 3. Execute (handles sync/async)
result = await tool.run(**tool_call.arguments)

# 4. Format result
tool_result_message = {
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": str(result)
}

# 5. Add to memory
memory.add("tool", result, tool_call_id=tool_call.id)
```

### Async/Sync Handling

```python
async def run(self, **kwargs) -> Any:
    """Execute tool, handling both sync and async functions"""

    # Validate arguments
    _validate_arguments(kwargs, self.schema)

    # Check if function is async
    if asyncio.iscoroutinefunction(self.func):
        return await self.func(**kwargs)
    else:
        # Run sync function in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.func(**kwargs)
        )
```

### Error Handling

```python
async def run(self, **kwargs) -> Any:
    """Execute tool with error handling"""

    try:
        # Validate and execute
        result = await self._execute(**kwargs)
        return result

    except ValidationError as e:
        # Argument validation error
        return f"Tool argument error: {e}"

    except Exception as e:
        # Tool execution error
        error_msg = f"Tool '{self.name}' error: {str(e)}"
        logger.error(error_msg)
        return error_msg
```

---

## Tool Registry in Agents

### BaseAgent Tool Management

```python
class BaseAgent:
    def __init__(self, tools: list[Any]):
        # Validate all items are Tool objects
        for item in tools:
            if not isinstance(item, Tool):
                raise TypeError(
                    f"All tools must be Tool objects, got {type(item)}"
                )

        # Build name-to-tool map
        self._tool_map: dict[str, Tool] = {
            tool.name: tool for tool in tools
        }

        self.tools = tools
```

### ReactAgent Usage

```python
class ReactAgent(BaseAgent):
    async def run(self, task: str) -> str:
        # Initialize memory
        self._memory.add("system", system_prompt)
        self._memory.add("user", task)

        # Get adapter
        adapter = get_adapter(self.model, self.tools, self.tool_calling_mode)

        while not done:
            # Format request with tools
            tool_params = await adapter.format_request(self.tools)
            messages = self._memory.to_list()

            # LLM call
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                **tool_params
            )

            # Extract tool call
            tool_call = await adapter.extract_tool_call(
                response,
                self._tool_map
            )

            if tool_call:
                # Execute tool
                tool = self._tool_map[tool_call.name]
                result = await tool.run(**tool_call.arguments)

                # Add to memory
                self._memory.add(
                    "tool",
                    result,
                    tool_call_id=tool_call.id
                )
            else:
                # Final answer
                return response.choices[0].message.content
```

---

## Tool Patterns

### Pattern 1: Simple Tool

```python
@tool
def calculator(expression: str) -> float:
    """Evaluate a mathematical expression"""
    return eval(expression)
```

### Pattern 2: Async Tool

```python
@tool
async def fetch_url(url: str) -> str:
    """Fetch content from a URL"""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text
```

### Pattern 3: Tool with Context

```python
@tool
def database_query(sql: str) -> list[dict]:
    """Execute SQL query against database"""
    # Uses injected database connection
    db = get_database_connection()
    return db.execute(sql)
```

### Pattern 4: Multi-step Tool

```python
@tool
async def research_topic(topic: str) -> str:
    """Research a topic using multiple sources"""
    # Search web
    results = await web_search(topic)

    # Browse top results
    content = ""
    for url in results[:3]:
        page = await web_browse(url)
        content += f"\n\n{page}"

    # Summarize
    summary = await summarize(content)
    return summary
```

---

## Tool Validation

**Location:** `/Users/tuna/tinyAgent/tinyagent/tools/validation.py`

### Static Analysis

```python
def validate_tool_class(tool_class: type) -> list[str]:
    """Validate a tool class for common issues"""

    issues = []

    # Check all methods have @tool decorator
    for name, method in inspect.getmembers(tool_class, predicate=inspect.isfunction):
        if not name.startswith("_"):
            if not hasattr(method, "__tool__"):
                issues.append(f"Method '{name}' missing @tool decorator")

    # Check for type hints
    hints = get_type_hints(tool_class)
    for name, method in inspect.getmembers(tool_class, predicate=inspect.isfunction):
        if name not in hints:
            issues.append(f"Method '{name}' missing type hints")

    return issues
```

### Runtime Validation

```python
def validate_tool_call(
    tool_call: ToolCall,
    tool: Tool
) -> bool:
    """Validate tool call against schema"""

    try:
        # Check tool exists
        if tool.name != tool_call.name:
            return False

        # Validate arguments
        validate_schema(tool_call.arguments, tool.schema)
        return True

    except ValidationError:
        return False
```

---

## Performance Considerations

### Tool Call Overhead

| Component | Overhead | Optimization |
|-----------|----------|--------------|
| Schema generation | One-time | Cache schema |
| Adapter selection | O(1) | Factory pattern |
| Argument validation | O(n) | Skip in production |
| Async/sync handling | Minimal | Thread pool |

### Optimization Strategies

1. **Cache Schemas:**
   ```python
   # Generate once, reuse
   tool._schema = generate_schema(tool.func)
   ```

2. **Batch Tool Calls:**
   ```python
   # Execute multiple tools concurrently
   results = await asyncio.gather(*[
       tool.run(**args) for tool in tools
   ])
   ```

3. **Lazy Loading:**
   ```python
   # Load heavy tools on first use
   @tool
   def heavy_tool():
       if not hasattr(heavy_tool, "_loaded"):
           heavy_tool._loaded = load_heavy_resource()
       return heavy_tool._loaded
   ```

---

## Related Documentation

- **Agent Hierarchy**: `/docs/architecture/agent-hierarchy.md`
- **Design Patterns**: `/docs/architecture/design-patterns.md`
- **Data Flow**: `/docs/architecture/data-flow.md`
- **Dependencies**: `/docs/architecture/dependencies.md`
