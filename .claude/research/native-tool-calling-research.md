# Native Tool Calling Research Report

**Research Date:** 2026-01-01
**Topic:** OpenAI-style Native Tool Calling vs JSON Parsing Approach
**Purpose:** Understand native function/tool calling implementations for OpenAI and Anthropic Claude APIs

---

## Executive Summary

Native tool calling is a structured API-based approach that provides reliable function invocation by LLMs. It replaces fragile JSON parsing methods with dedicated API responses containing structured tool call data. Both OpenAI and Anthropic Claude have implemented native tool calling with similar concepts but different API structures.

---

## Table of Contents

1. [JSON Parsing vs Native Tool Calling](#1-json-parsing-vs-native-tool-calling)
2. [OpenAI Native Tool Calling](#2-openai-native-tool-calling)
3. [Anthropic Claude Tool Use](#3-anthropic-claude-tool-use)
4. [Migration Path](#4-migration-path)
5. [Best Practices](#5-best-practices)
6. [Code Examples](#6-code-examples)

---

## 1. JSON Parsing vs Native Tool Calling

### 1.1 JSON Parsing (Traditional Approach)

**How it works:**
- Instruct the LLM via prompt to output JSON
- Parse response text using `JSON.parse()` or similar
- Handle parsing failures with retries

**Disadvantages:**
- Prone to parsing failures when LLM outputs malformed JSON
- LLM might wrap JSON in explanatory text
- Requires multiple attempts and retry logic
- Less reliable for production use

### 1.2 Native Tool Calling (Structured API)

**How it works:**
- Uses dedicated tool/function schemas in API requests
- Model returns structured tool calls in separate response fields
- Built-in error handling and validation
- Cleaner separation between reasoning and tool execution

**Advantages:**
- Higher reliability and production-ready
- Better error handling
- Native model support for structured outputs
- Parallel function calling support
- Strict schema validation

**Sources:**
- [Function calling | OpenAI API](https://platform.openai.com/docs/guides/function-calling)
- [JSON mode vs Function Calling - API](https://community.openai.com/t/json-mode-vs-function-calling/476994)
- [OpenAI JSON Mode vs. Function Calling for Data Extraction](https://developers.llamaindex.ai/python/examples/llm/openai_json_vs_function_calling/)

---

## 2. OpenAI Native Tool Calling

### 2.1 OpenAI APIs: Two Approaches

OpenAI has two main APIs for tool calling:

1. **Chat Completions API** (Legacy format)
2. **Responses API** (Newer, recommended format)

### 2.2 OpenAI Responses API (Recommended)

The Responses API uses a cleaner format with `function_call` and `function_call_output` types.

#### 2.2.1 Defining Tools

Tools are defined in the `tools` parameter as an array of function definitions:

```python
tools = [
    {
        "type": "function",
        "name": "get_weather",
        "description": "Retrieves current weather for the given location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and country e.g. Bogota, Colombia"
                },
                "units": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Units the temperature will be returned in."
                }
            },
            "required": ["location", "units"],
            "additionalProperties": False
        },
        "strict": True
    }
]
```

**Function Schema Properties:**
- `type`: Always `"function"`
- `name`: Function name (e.g., `"get_weather"`)
- `description`: When and how to use the function
- `parameters`: JSON Schema defining input arguments
- `strict`: (Optional) Enforce strict schema adherence

#### 2.2.2 Tool Choice Parameter

Controls when functions are called:

| Value | Description |
|-------|-------------|
| `"auto"` | (Default) Model decides whether to call functions |
| `"required"` | Model must call one or more functions |
| `"none"` | No functions will be called |
| `{"type": "function", "name": "func_name"}` | Force a specific function |
| `{"type": "allowed_tools", "mode": "auto", "tools": [...]}` | Restrict to subset of tools |

#### 2.2.3 Tool Calling Flow (5 Steps)

1. Make request to model with tools
2. Receive tool call from model
3. Execute code on application side
4. Send second request with tool output
5. Receive final response

#### 2.2.4 Response Structure

**Tool Call Response:**
```python
response.output = [
    {
        "id": "fc_12345xyz",
        "call_id": "call_12345xyz",
        "type": "function_call",
        "name": "get_weather",
        "arguments": '{"location":"Paris, France"}'
    }
]
```

**Handling Multiple Tool Calls:**
```python
for tool_call in response.output:
    if tool_call.type != "function_call":
        continue

    name = tool_call.name
    args = json.loads(tool_call.arguments)

    result = call_function(name, args)

    # Append result
    input_messages.append({
        "type": "function_call_output",
        "call_id": tool_call.call_id,
        "output": str(result)
    })
```

#### 2.2.5 Submitting Function Results

After executing functions, submit results back:

```python
response = client.responses.create(
    model="gpt-4.1",
    input=input_messages,
    tools=tools,
)
```

### 2.3 OpenAI Chat Completions API (Legacy)

**Note:** The `function_call` parameter is deprecated. Use `tool_calls` instead.

#### 2.3.1 Request Format

```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "What's the weather in Paris?"}
    ],
    tools=tools,
    tool_choice="auto"
)
```

#### 2.3.2 Response Format

```python
{
    "choices": [{
        "message": {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_abc123",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"location": "Paris, France"}'
                    }
                }
            ]
        },
        "finish_reason": "tool_calls"
    }]
}
```

#### 2.3.3 Submitting Tool Results

```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "What's the weather in Paris?"},
        {
            "role": "assistant",
            "tool_calls": tool_calls  # from previous response
        },
        {
            "role": "tool",
            "tool_call_id": "call_abc123",
            "content": '{"temperature": 22, "unit": "celsius"}'
        }
    ],
    tools=tools
)
```

**Key Differences from Responses API:**
- Uses `tool_calls` array in assistant message
- Uses separate `"role": "tool"` message for results
- Uses `tool_call_id` instead of `call_id`
- `finish_reason` is `"tool_calls"` instead of checking output types

### 2.4 OpenAI Additional Features

#### 2.4.1 Strict Mode

When `"strict": true`, function calls reliably adhere to schema:

**Requirements:**
1. `additionalProperties` must be `false` for all objects
2. All fields must be marked as `required`

**Optional fields pattern:**
```python
"units": {
    "type": ["string", "null"],  # Union with null
    "enum": ["celsius", "fahrenheit"]
}
```

#### 2.4.2 Parallel Function Calling

Model can call multiple functions in one turn. Disable with:
```python
parallel_tool_calls=False
```

#### 2.4.3 Streaming

```python
stream = client.responses.create(
    model="gpt-4.1",
    input=[{"role": "user", "content": "What's the weather in Paris?"}],
    tools=tools,
    stream=True
)

for event in stream:
    if event.type == "response.output_item.added":
        final_tool_calls[event.output_index] = event.item
    elif event.type == "response.function_call_arguments.delta":
        index = event.output_index
        if final_tool_calls[index]:
            final_tool_calls[index].arguments += event.delta
```

**Sources:**
- [Function calling | OpenAI API](https://platform.openai.com/docs/guides/function-calling)
- [Structured model outputs | OpenAI API](https://platform.openai.com/docs/guides/structured-outputs)
- [How to call functions with chat models - OpenAI Cookbook](https://cookbook.openai.com/examples/how_to_call_functions_with_chat_models)
- [Chat Completions | OpenAI API Reference](https://platform.openai.com/docs/api-reference/chat)

---

## 3. Anthropic Claude Tool Use

### 3.1 Tool Definition Format

```python
tools = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and country, e.g., Paris, France"
                }
            },
            "required": ["location"]
        }
    }
]
```

**Key Difference:** Uses `input_schema` instead of `parameters`.

### 3.2 Making Requests

```python
import anthropic

client = anthropic.Anthropic()

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=tools,
    messages=[
        {"role": "user", "content": "What's the weather in Paris?"}
    ]
)
```

### 3.3 Response Structure with tool_use Blocks

```python
{
    "id": "msg_abc123",
    "type": "message",
    "role": "assistant",
    "content": [
        {
            "type": "tool_use",
            "id": "toolu_abc123",
            "name": "get_weather",
            "input": {"location": "Paris, France"}
        }
    ],
    "stop_reason": "tool_use"
}
```

**Key Fields:**
- `type`: `"tool_use"` for tool call blocks
- `id`: Unique identifier for the tool use
- `name`: Function name
- `input`: Function arguments (already parsed, not JSON string)
- `stop_reason`: `"tool_use"` when tool calls present

### 3.4 Extracting Tool Calls

```python
for block in message.content:
    if block.type == "tool_use":
        tool_name = block.name
        tool_input = block.input
        tool_use_id = block.id

        # Execute function
        result = get_weather(**tool_input)

        # Build result response
        response_messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": json.dumps(result)
                }
            ]
        })
```

### 3.5 Submitting Tool Results

```python
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=tools,
    messages=[
        {"role": "user", "content": "What's the weather in Paris?"},
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_abc123",
                    "name": "get_weather",
                    "input": {"location": "Paris, France"}
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_abc123",
                    "content": '{"temperature": 22, "unit": "celsius"}'
                }
            ]
        }
    ]
)
```

**Important:** Tool result blocks must immediately follow their corresponding tool use blocks in message history.

### 3.6 Claude Tool Use Features

- **Content blocks array:** Responses can contain both text and tool_use blocks
- **Parsed input:** Arguments are already parsed objects, not JSON strings
- **Multiple tool calls:** Single response can contain multiple tool_use blocks
- **Tool results:** Use `tool_result` content block type with `tool_use_id`

**Sources:**
- [Tool use with Claude - Claude Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)
- [How to implement tool use - Claude Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use)
- [Create a Message - Claude API Reference](https://platform.claude.com/docs/en/api/messages/create)
- [Introducing advanced tool use on the Claude Developer Platform](https://www.anthropic.com/engineering/advanced-tool-use)

---

## 4. Migration Path

### 4.1 From JSON Parsing to Native Tool Calling

**Before (JSON Parsing):**
```python
# Prompt instructs model to output JSON
prompt = "Output your answer as JSON with keys: name, age"

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}]
)

# Fragile parsing
try:
    result = json.loads(response.choices[0].message.content)
except json.JSONDecodeError:
    # Retry or handle error
    pass
```

**After (Native Tool Calling):**
```python
# Define function schema
tools = [{
    "type": "function",
    "name": "extract_person",
    "description": "Extract person information",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"}
        },
        "required": ["name", "age"],
        "additionalProperties": False
    },
    "strict": True
}]

response = client.responses.create(
    model="gpt-4.1",
    input=[{"role": "user", "content": "Extract info from: John is 25"}],
    tools=tools
)

# Structured, reliable extraction
for tool_call in response.output:
    if tool_call.type == "function_call":
        result = json.loads(tool_call.arguments)
        # result = {"name": "John", "age": 25}
```

### 4.2 From OpenAI to Anthropic

**Key Differences:**

| Aspect | OpenAI Responses API | Anthropic Claude |
|--------|---------------------|------------------|
| Schema field | `parameters` | `input_schema` |
| Tool call type | `function_call` | `tool_use` |
| Arguments format | JSON string | Parsed object |
| ID field | `call_id` | `id` (in tool_use) |
| Result submission | `function_call_output` type | `tool_result` content block |
| Result ID reference | `call_id` | `tool_use_id` |
| Response structure | `output` array | `content` array |
| Stop indicator | Check output types | `stop_reason: "tool_use"` |

**Sources:**
- [OpenAI Function Calling Tutorial for Developers](https://www.vellum.ai/blog/openai-function-calling-tutorial)
- [The Missing Guide to Native Tool & Function Calling](https://taylorwilsdon.medium.com/the-missing-guide-to-native-tool-function-calling-with-mcp-openapi-servers-ed2557a8a7b7)

---

## 5. Best Practices

### 5.1 Function/Tool Schema Design

1. **Clear Names and Descriptions**
   - Use descriptive function names
   - Explicitly describe purpose of each parameter
   - Include format information in descriptions
   - Use system prompt to describe when to use functions

2. **Software Engineering Principles**
   - Make functions obvious and intuitive
   - Use enums to make invalid states unrepresentable
   - "Pass the intern test" - can a human use it correctly?

3. **Minimize Model Burden**
   - Don't make model fill arguments you already know
   - Combine functions always called in sequence
   - Keep number of functions small (< 20 recommended)

4. **Schema Validation**
   - Always enable `strict: true` for OpenAI
   - Use `additionalProperties: false`
   - Mark all fields as required (use `null` type for optional)

### 5.2 Error Handling

- **Validate function results** before sending to model
- **Implement retry logic** for failed tool calls
- **Handle malformed arguments** gracefully
- **Log tool calls** for debugging
- **Set timeouts** for function execution

### 5.3 Token Management

- Functions count against context limit (injected into system message)
- Use **prompt caching** for large tool lists
- Consider **fine-tuning** to reduce token usage for many functions
- Limit function descriptions if hitting token limits

### 5.4 Performance Optimization

- **Batch function calls** when possible
- **Use parallel function calling** for independent operations
- **Cache function results** for repeated calls
- **Profile tool execution time**

**Sources:**
- [Best practices for defining functions](https://platform.openai.com/docs/guides/function-calling#best-practices-for-defining-functions)
- [Reducing Tool Calling Error Rates from 15% to 3%](https://mastra.ai/blog/mcp-tool-compatibility-layer)
- [Writing effective tools for AI agents—using Claude](https://www.anthropic.com/engineering/writing-tools-for-agents)

---

## 6. Code Examples

### 6.1 Complete OpenAI Responses API Example

```python
from openai import OpenAI
import json

client = OpenAI()

# 1. Define tools
tools = [
    {
        "type": "function",
        "name": "get_weather",
        "description": "Get current weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and country e.g. Paris, France"
                },
                "units": {
                    "type": ["string", "null"],
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Temperature units"
                }
            },
            "required": ["location", "units"],
            "additionalProperties": False
        },
        "strict": True
    }
]

# 2. Define function implementations
def get_weather(location: str, units: str = "celsius") -> dict:
    # Actual weather API call would go here
    return {"temperature": 22, "unit": units, "conditions": "sunny"}

# 3. Create input list
input_list = [
    {"role": "user", "content": "What's the weather in Paris?"}
]

# 4. Initial request
response = client.responses.create(
    model="gpt-4.1",
    tools=tools,
    input=input_list,
)

# 5. Process tool calls
input_list.extend(response.output)

for item in response.output:
    if item.type == "function_call" and item.name == "get_weather":
        # Parse arguments
        args = json.loads(item.arguments)

        # Execute function
        result = get_weather(**args)

        # Add result to input
        input_list.append({
            "type": "function_call_output",
            "call_id": item.call_id,
            "output": json.dumps(result)
        })

# 6. Get final response
final_response = client.responses.create(
    model="gpt-4.1",
    tools=tools,
    input=input_list,
)

print(final_response.output_text)
# Output: "The weather in Paris is 22°C and sunny."
```

### 6.2 Complete Anthropic Claude Example

```python
import anthropic
import json

client = anthropic.Anthropic()

# 1. Define tools
tools = [
    {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and country e.g. Paris, France"
                }
            },
            "required": ["location"]
        }
    }
]

# 2. Define function
def get_weather(location: str) -> dict:
    return {"temperature": 22, "unit": "celsius", "conditions": "sunny"}

# 3. Build messages list
messages = [
    {"role": "user", "content": "What's the weather in Paris?"}
]

# 4. Initial request
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=tools,
    messages=messages
)

# 5. Process tool_use blocks
assistant_content = []
for block in response.content:
    assistant_content.append(block.model_dump())

    if block.type == "tool_use":
        # Execute function
        result = get_weather(**block.input)

        # Add assistant message with tool_use
        messages.append({
            "role": "assistant",
            "content": assistant_content
        })

        # Add user message with tool_result
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result)
                }
            ]
        })

        # Get final response
        final_response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            tools=tools,
            messages=messages
        )

        print(final_response.content[0].text)
        # Output: "The weather in Paris is 22°C and sunny."
        break
```

### 6.3 Parallel Function Calling Example (OpenAI)

```python
tools = [
    {
        "type": "function",
        "name": "get_weather",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            },
            "required": ["location"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "get_time",
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {"type": "string"}
            },
            "required": ["timezone"],
            "additionalProperties": False
        },
        "strict": True
    }
]

response = client.responses.create(
    model="gpt-4.1",
    input=[{"role": "user", "content": "What's the weather and time in Paris and Tokyo?"}],
    tools=tools
)

# Handle multiple parallel calls
for item in response.output:
    if item.type == "function_call":
        args = json.loads(item.arguments)
        if item.name == "get_weather":
            result = get_weather(**args)
        elif item.name == "get_time":
            result = get_time(**args)

        input_list.append({
            "type": "function_call_output",
            "call_id": item.call_id,
            "output": json.dumps(result)
        })
```

---

## Summary of Key Differences

| Aspect | JSON Parsing | OpenAI Native | Anthropic Native |
|--------|--------------|---------------|------------------|
| **Reliability** | Low | High | High |
| **Validation** | Manual | Built-in (strict mode) | Built-in |
| **Arguments format** | JSON string in text | JSON string | Parsed object |
| **Parallel calls** | Manual | Supported | Supported |
| **Error handling** | Custom retry logic | API-level | API-level |
| **Token efficiency** | High | Medium (schema overhead) | Medium |
| **Migration effort** | N/A | From JSON parsing | From OpenAI or JSON |

---

## Recommended Implementation Strategy

1. **Start with OpenAI Responses API** for new projects
2. **Enable strict mode** (`strict: true`) for reliable schema validation
3. **Use clear, detailed descriptions** for all functions and parameters
4. **Implement proper error handling** with retry logic
5. **Log all tool calls** for debugging and analytics
6. **Consider abstraction layer** to support multiple providers (OpenAI, Anthropic)

---

## References

### OpenAI Documentation
- [Function calling | OpenAI API](https://platform.openai.com/docs/guides/function-calling)
- [Structured model outputs | OpenAI API](https://platform.openai.com/docs/guides/structured-outputs)
- [Chat Completions | OpenAI API Reference](https://platform.openai.com/docs/api-reference/chat)
- [Responses | OpenAI API Reference](https://platform.openai.com/docs/api-reference/responses)
- [How to call functions with chat models - OpenAI Cookbook](https://cookbook.openai.com/examples/how_to_call_functions_with_chat_models)

### Anthropic Documentation
- [Tool use with Claude - Claude Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)
- [How to implement tool use - Claude Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use)
- [Create a Message - Claude API Reference](https://platform.claude.com/docs/en/api/messages/create)
- [Introducing advanced tool use on the Claude Developer Platform](https://www.anthropic.com/engineering/advanced-tool-use)
- [Writing effective tools for AI agents—using Claude](https://www.anthropic.com/engineering/writing-tools-for-agents)

### Community Resources
- [The Missing Guide to Native Tool & Function Calling](https://taylorwilsdon.medium.com/the-missing-guide-to-native-tool-function-calling-with-mcp-openapi-servers-ed2557a8a7b7)
- [Reducing Tool Calling Error Rates from 15% to 3%](https://mastra.ai/blog/mcp-tool-compatibility-layer)
- [OpenAI Function Calling Tutorial for Developers](https://www.vellum.ai/blog/openai-function-calling-tutorial)
- [A Guide to Function Calling in OpenAI](https://mirascope.com/blog/openai-function-calling)
- [Guide to structured outputs and function calling with LLMs](https://agenta.ai/blog/the-guide-to-structured-outputs-and-function-calling-with-llms)

---

**Document Status:** Research Complete
**Last Updated:** 2026-01-01
**Version:** 1.0
