# tinyAgent Tools Framework

This document provides a comprehensive guide to the tools framework in tinyAgent, including how to create, use, and extend tools.

## What Are Tools?

In tinyAgent, tools are the functional units that the Agent can execute to accomplish tasks. Each tool:

1. Has a unique name
2. Has a descriptive explanation of what it does
3. Defines parameters it accepts and their types
4. Implements a specific function
5. Returns a result that can be used by the Agent

Tools are the primary way to extend tinyAgent's capabilities, allowing it to perform a wide range of tasks from simple calculations to complex API interactions.

## Tool Types

tinyAgent supports several types of tools:

1. **Python Tools** - Written directly in Python using the `Tool` class or `@tool` decorator
2. **External Tools** - Written in other languages (Go, Rust, C/C++, etc.) with JSON communication
3. **MCP Tools** - Provided by MCP servers, extending capabilities dynamically

## Creating Python Tools

### Using the Tool Class

The most direct way to create a tool is by instantiating the `Tool` class:

```python
from core import Tool, ParamType

def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two integers."""
    return a + b

sum_tool = Tool(
    name="calculate_sum",
    description="Calculate the sum of two integers",
    parameters={
        "a": ParamType.INTEGER,
        "b": ParamType.INTEGER
    },
    func=calculate_sum
)
```

### Using the @tool Decorator

For a more concise approach, you can use the `@tool` decorator:

```python
from core import tool

@tool
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two integers."""
    return a + b

# The decorator automatically creates a Tool instance
# based on the function's signature and docstring
```

The decorator can also take arguments to customize the tool:

```python
@tool(name="add_numbers", rate_limit=5)
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two integers."""
    return a + b
```

## Parameter Types

tinyAgent supports the following parameter types via the `ParamType` enum:

- `ParamType.STRING` - For text values
- `ParamType.INTEGER` - For whole numbers
- `ParamType.FLOAT` - For decimal numbers
- `ParamType.ANY` - For any type of value

When using the `@tool` decorator, parameter types are inferred from Python type hints:

```python
@tool
def format_name(first: str, last: str, age: int) -> str:
    """Format a person's name and age."""
    return f"{first} {last} is {age} years old"
# Equivalent to:
# parameters={"first": ParamType.STRING, "last": ParamType.STRING, "age": ParamType.INTEGER}
```

## Tool Factory and Registration

Tools are now managed through the `AgentFactory`, which provides centralized tool registration, execution, and tracking:

```python
from core.factory.agent_factory import AgentFactory
from core.agent import Agent

# Get the singleton factory instance
factory = AgentFactory.get_instance()

# Create and register a tool
factory.create_tool(
    name="calculator",
    description="Perform basic arithmetic operations",
    func=calculate
)

# Create an agent that will use the factory
agent = Agent(factory=factory)

# Run the agent with a query
result = agent.run("Calculate 5 + 3")
print(result)  # Output: 8
```

This approach ensures proper tool tracking and rate limiting. The factory automatically:

1. Registers tools with unique names
2. Tracks usage statistics for each tool
3. Enforces rate limits
4. Provides a centralized execution path

### Direct Tool Registration

You can also register existing Tool instances with the factory:

```python
# Create a tool
my_tool = Tool(
    name="my_tool",
    description="My custom tool",
    parameters={"param": ParamType.STRING},
    func=my_function
)

# Register with the factory
factory.register_tool(my_tool)
```

## Tool Execution Flow

All tool executions now go through the factory to ensure consistent tracking and rate limiting:

```python
# Bad: Direct tool invocation (bypasses tracking & rate limiting)
# result = my_tool(param="value")  # Don't do this!

# Good: Factory-mediated execution
result = factory.execute_tool("my_tool", param="value")
```

When using an Agent, tool execution is automatically handled through the factory:

```python
# Agent.run will use factory.execute_tool internally
result = agent.run("Use my_tool with value")
```

## Creating Cross-Language Tools

One of tinyAgent's most powerful features is the ability to incorporate tools written in other programming languages through a standardized JSON interface.

### JSON Communication Protocol

External tools communicate with tinyAgent through a simple JSON protocol:

1. **Input**: The tool receives a JSON object through stdin containing the tool parameters
2. **Processing**: The tool processes the input and generates a result
3. **Output**: The tool returns a JSON object through stdout containing the result

### Manifest File

External tools require a `manifest.json` file that defines the tool's metadata:

```json
{
  "name": "text_rank",
  "description": "Extract key sentences from text using TextRank algorithm",
  "parameters": {
    "text": {
      "type": "string",
      "description": "The text to analyze"
    },
    "num_sentences": {
      "type": "integer",
      "description": "Number of key sentences to extract",
      "default": 3
    }
  },
  "command": "./text_rank",
  "working_directory": "./external_tools/text_rank/"
}
```

### Example: C Implementation

Here's an example of a tool implemented in C:

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <json-c/json.h>

int main() {
    // Read JSON from stdin
    char buffer[4096];
    fgets(buffer, sizeof(buffer), stdin);
    
    // Parse input JSON
    struct json_object *input_json = json_tokener_parse(buffer);
    
    // Extract parameters
    struct json_object *text_obj, *num_sentences_obj;
    json_object_object_get_ex(input_json, "text", &text_obj);
    json_object_object_get_ex(input_json, "num_sentences", &num_sentences_obj);
    
    const char *text = json_object_get_string(text_obj);
    int num_sentences = json_object_get_int(num_sentences_obj);
    
    // Process text using your algorithm
    // ... (implementation of text processing)
    
    // Create result JSON
    struct json_object *result_json = json_object_new_object();
    struct json_object *sentences_array = json_object_new_array();
    
    // Add extracted sentences to array
    for (int i = 0; i < num_sentences; i++) {
        // Example - in real code, you'd use your algorithm's results
        char sentence[100];
        sprintf(sentence, "This is extracted sentence %d", i+1);
        json_object_array_add(sentences_array, json_object_new_string(sentence));
    }
    
    json_object_object_add(result_json, "sentences", sentences_array);
    
    // Output result JSON
    printf("%s\n", json_object_to_json_string(result_json));
    
    // Cleanup
    json_object_put(input_json);
    json_object_put(result_json);
    
    return 0;
}
```

### Example: Rust Implementation

For performance-critical tools, languages like Rust offer excellent speed and safety:

```rust
use serde::{Deserialize, Serialize};
use std::io::{self, Read};

#[derive(Deserialize)]
struct Input {
    text: String,
    num_sentences: Option<usize>,
}

#[derive(Serialize)]
struct Output {
    sentences: Vec<String>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Read JSON from stdin
    let mut buffer = String::new();
    io::stdin().read_to_string(&mut buffer)?;
    
    // Parse input
    let input: Input = serde_json::from_str(&buffer)?;
    let num_sentences = input.num_sentences.unwrap_or(3);
    
    // Process text - this would use your actual algorithm
    let sentences = extract_key_sentences(&input.text, num_sentences);
    
    // Create and output result
    let output = Output { sentences };
    println!("{}", serde_json::to_string(&output)?);
    
    Ok(())
}

fn extract_key_sentences(text: &str, count: usize) -> Vec<String> {
    // This is where your TextRank or other algorithm would be implemented
    // Just a placeholder implementation for the example
    text.split('.')
        .take(count)
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect()
}
```

### Loading External Tools

External tools are loaded using the `load_external_tools` function:

```python
from core.tools import load_external_tools

# Load external tools from a directory
external_tools = load_external_tools("/path/to/tools")

# Register with the factory
factory = AgentFactory.get_instance()
for tool in external_tools:
    factory.register_tool(tool)
```

## Built-in Tools

tinyAgent includes several built-in tools that provide common functionality:

### anon_coder

Executes Python code safely with configurable security checks:

```python
from core.tools import anon_coder_tool

# Direct usage through factory
result = factory.execute_tool(
    "anon_coder",
    code="print([x**2 for x in range(10)])",
    timeout=5
)
```

Security settings for code execution can be configured in `config.yml`:

```yaml
# Code execution security configuration
code_execution:
  # Allow potentially dangerous operations (file operations, etc)
  allow_dangerous_operations: false  # Set to true to disable security restrictions
  
  # Optional: more granular control
  allowed_operations:
    file_operations: false
    os_operations: false
    imports: ["os", "sys"]  # Additional allowed imports beyond the defaults
```

This allows for balancing security with functionality based on your specific needs and trust level.

### llm_serializer

Uses LLMs to convert complex objects to JSON-compatible formats:

```python
from core.tools import llm_serializer_tool

# Convert a complex object to JSON via factory
result = factory.execute_tool(
    "llm_serializer",
    obj_type="CustomClass",
    obj_repr=str(my_complex_object)
)
```

### ripgrep

Searches files using the ripgrep tool:

```python
# Search for a pattern in files via factory
result = factory.execute_tool(
    "ripgrep",
    pattern="TODO",
    path="src/",
    flags="-i"
)
```

## Tool Error Handling

Tools should handle errors gracefully and return informative error messages:

```python
@tool
def divide(a: float, b: float) -> float:
    """Divide two numbers."""
    try:
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    except Exception as e:
        raise ToolError(f"Division failed: {str(e)}")
```

The Agent class will catch and handle exceptions raised by tools, including:

- `ToolError` - General tool execution errors
- `ToolNotFoundError` - When a tool is not found
- `ToolExecutionError` - When a tool execution fails
- `RateLimitExceeded` - When a tool's rate limit is exceeded

## Rate Limiting

Tools can have rate limits to prevent excessive usage:

```python
# Tool class with rate limit
api_tool = Tool(
    name="api_call",
    description="Call an external API",
    parameters={"query": ParamType.STRING},
    func=make_api_call,
    rate_limit=10  # Max 10 calls per session
)

# Decorator with rate limit
@tool(rate_limit=5)
def limited_function(param: str) -> str:
    """A rate-limited function."""
    return f"Processed: {param}"

# Factory with rate limit
factory.create_tool(
    name="expensive_api",
    description="Call an expensive API",
    func=call_expensive_api,
    rate_limit=5
)
```

Rate limits can also be configured globally in `config.yml`:

```yaml
# Rate limiting configuration
rate_limits:
  global_limit: 30  # Default limit for all tools
  tool_limits:      # Tool-specific limits
    web_search: 10
    code_execution: 5
    api_call: 20
```

## Monitoring Tool Usage

The factory provides methods to monitor tool usage:

```python
# Get current status
status = factory.get_status()

print("\nTool usage statistics:")
for tool_name, stats in status["tools"].items():
    print(f"  {tool_name}: {stats['calls']}/{stats['limit']} calls")
```

## Best Practices

### Naming

Tool names should be:
- Lowercase
- No spaces (use underscores)
- Descriptive of what the tool does
- Concise

### Descriptions

Tool descriptions should:
- Clearly explain what the tool does
- Include examples of usage
- Specify any requirements or limitations
- Be detailed enough for the LLM to understand when to use it

### Parameters

Parameter design should:
- Use clear, descriptive names
- Use the appropriate type for each parameter
- Include only necessary parameters
- Use default values where appropriate

### Implementation

Tool implementation should:
- Handle errors gracefully with informative messages
- Validate inputs before processing
- Be efficient and avoid unnecessary computation
- Clean up any resources (files, connections) it uses

### Cross-Language Tools

When creating tools in other languages:
- Use standard JSON libraries for your language
- Implement proper error handling and report errors in the JSON response
- Keep the tool focused on a single capability
- Consider performance characteristics (startup time, memory usage)
- Document any dependencies or installation requirements

## Conclusion

Tools are the core extension mechanism for tinyAgent. By creating and using tools, you can extend tinyAgent's capabilities to handle a wide range of tasks. 

The flexibility of the tools framework allows for tools to be written in Python or other languages, making it easy to leverage:

1. High-performance libraries in languages like Rust or C++
2. Existing code bases in any language
3. Language-specific capabilities (e.g., GPU programming, system-level operations)
4. Specialized algorithms with better implementations in other languages

The standardized JSON interface creates a universal language for tool communication, enabling truly polyglot agent systems while maintaining a simple, consistent approach to tool usage.
