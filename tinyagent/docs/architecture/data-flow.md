---
title: Data Flow Architecture
path: architecture/
type: directory
depth: 0
description: Data transformation pipeline and component interactions
seams: [A]
---

# Data Flow Architecture

## Overview

This document traces the complete data flow from user request to final output through the tinyAgent framework. Understanding this flow is critical for debugging, optimization, and extending the system.

---

## High-Level Pipeline

```
User Request → Initialization → ReAct Loop → Execution → Memory Update → Output
                     ↓              ↓           ↓
                  Memory         Tools      Executor
```

---

## 1. Input Phase

### 1.1 Agent Initialization

**ReactAgent:**

```python
agent = ReactAgent(
    model="gpt-4",
    tools=[search_tool, calculator],
    tool_calling_mode="auto"
)
```

**TinyCodeAgent:**

```python
agent = TinyCodeAgent(
    model="gpt-4",
    tools=[search_tool, file_reader],
    executor=LocalExecutor(trust_level=TrustLevel.LOCAL)
)
```

### 1.2 Memory Initialization

**ReactAgent (Simple Memory):**

```python
# core/memory.py
self._memory = Memory()
self._memory.add("system", system_prompt)
self._memory.add("user", user_task)
```

**TinyCodeAgent (Structured Memory):**

```python
# memory/manager.py
self._memory_manager = MemoryManager()
self._memory_manager.add(SystemPromptStep(content=system_prompt))
self._memory_manager.add(TaskStep(task=user_task))
```

### 1.3 Additional Initialization

**TinyCodeAgent also sets up:**

```python
# Execution namespace preparation
self._executor.inject("search", search_tool.func)
self._executor.inject("final_answer", self._create_finalizer())
self._executor.inject("store", scratchpad.store)
self._executor.inject("recall", scratchpad.recall)

# Signal collection
set_signal_collector(self._handle_signal)
```

---

## 2. ReAct Loop Phase

### 2.1 Prepare LLM Request

**Convert memory to messages:**

**ReactAgent:**

```python
messages = self._memory.to_list()
# [
#   {"role": "system", "content": "..."},
#   {"role": "user", "content": "user task"}
# ]
```

**TinyCodeAgent:**

```python
messages = self._memory_manager.to_messages()
# Same format, but generated from Step objects
```

### 2.2 Format Tools

**ReactAgent (via Adapter):**

```python
adapter = get_adapter(model, tools, mode)
request_body = {
    "messages": messages,
    "tools": adapter.format_request(tools)  # Tool schemas
}
# For native tools:
# "tools": [
#   {
#     "type": "function",
#     "function": {
#       "name": "web_search",
#       "parameters": {
#         "type": "object",
#         "properties": {
#           "query": {"type": "string"}
#         }
#       }
#     }
#   }
# ]
```

**TinyCodeAgent (No tool formatting):**

```python
# Tools injected into code namespace, not in request
request_body = {
    "messages": messages
    # No tools parameter
}
```

### 2.3 LLM API Call

**Both agents:**

```python
response = await self._client.chat.completions.create(
    model=self.model,
    messages=messages,
    **tool_params  # Only for ReactAgent
)
```

---

## 3. Response Processing Phase

### 3.1 ReactAgent: Extract Tool Call

**Via Adapter:**

```python
tool_call = await adapter.extract_tool_call(response)

# Native tool response:
# {
#   "id": "call_abc123",
#   "type": "function",
#   "function": {
#     "name": "web_search",
#     "arguments": '{"query": "python help"}'
#   }
# }

# Parsed to:
# ToolCall(name="web_search", arguments={"query": "python help"})
```

### 3.2 TinyCodeAgent: Extract Code Block

**Parse markdown code block:**

```python
response_text = response.choices[0].message.content

# Extract from:
# ```python
# import requests
# result = web_search("python help")
# print(result)
# final_answer(result)
# ```

code = self._extract_code_block(response_text)
```

---

## 4. Execution Phase

### 4.1 ReactAgent: Execute Tool

```python
# Look up tool
tool = self._tool_map[tool_call.name]

# Execute (handles sync/async)
result = await tool.run(**tool_call.arguments)

# Format as tool result message
tool_message = {
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": str(result)
}
```

### 4.2 TinyCodeAgent: Execute Code

```python
# AST security check
self._executor._check_imports(code)

# Execute in namespace
output = await self._executor.run(code)

# Capture stdout and scratchpad state
execution_result = f"{output}\n{scratchpad.to_context()}"
```

**Executor Internals:**

```python
# execution/local.py
namespace = self._build_namespace()  # Safe built-ins + tools

# Redirect stdout
with capture_stdout() as output:
    exec(code, namespace)

# Check for final_answer
if "_final_result" in namespace:
    self._finalizer.set_answer(namespace["_final_result"])
```

---

## 5. Memory Update Phase

### 5.1 ReactAgent: Add to History

```python
# Add assistant message (with tool call)
self._memory.add(
    "assistant",
    reasoning,
    tool_call=tool_call
)

# Add tool result message
self._memory.add("tool", result, tool_call_id=tool_call.id)

# History now:
# [
#   {"role": "system", "content": "..."},
#   {"role": "user", "content": "task"},
#   {"role": "assistant", "content": "reasoning", "tool_calls": [...]},
#   {"role": "tool", "content": "result", "tool_call_id": "..."}
# ]
```

### 5.2 TinyCodeAgent: Create Action Step

```python
# Create structured step
action_step = ActionStep(
    reasoning=llm_reasoning,
    action="code_execution",
    code=code,
    observation=execution_result,
    signals=collected_signals,
    timestamp=datetime.now(),
    step_number=self._step_count
)

# Add to memory manager
self._memory_manager.add(action_step)

# Memory now contains:
# [
#   SystemPromptStep(...),
#   TaskStep(...),
#   ActionStep(reasoning="...", action="code_execution", ...),
#   ActionStep(reasoning="...", action="code_execution", ...)
# ]
```

---

## 6. Loop Decision Phase

### 6.1 Check for Completion

**ReactAgent:**

```python
# Check if LLM provided final answer
if "answer" in response:
    final = response["answer"]
    self._finalizer.set_answer(final)
    done = True
```

**TinyCodeAgent:**

```python
# Check if code called final_answer()
if self._finalizer.is_set:
    done = True
```

### 6.2 Check Step Limits

```python
if self._step_count >= self._max_steps:
    done = True
    state = "step_limit_reached"
```

### 6.3 Continue or Return

**If not done:**
- Return to step 2.1 (Prepare LLM Request)
- Updated memory provides context for next iteration

**If done:**
- Proceed to Output Phase

---

## 7. Output Phase

### 7.1 Construct Result

```python
# core/types.py
return RunResult(
    output=self._finalizer.answer.value,
    final_answer=self._finalizer.answer,
    state="completed",  # or "step_limit_reached"
    steps_taken=self._step_count,
    duration_seconds=time.time() - start_time
)
```

### 7.2 Return to User

**Simple output:**

```python
result = await agent.run("search for python help")
print(result.output)
# "Here are some Python resources..."
```

**Detailed result:**

```python
result = await agent.run("search for python help", return_result=True)
print(result.final_answer.metadata)
# {"confidence": 0.95, "sources": [...]}
print(result.steps_taken)
# 5
```

---

## Component Data Flow Diagrams

### ReactAgent Data Flow

```
┌─────────────┐
│  User Task  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│   Memory (list[Message])    │
│  - system                   │
│  - user                     │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   LLM Request Builder       │
│  - messages = memory.to_list│
│  - tools = adapter.format   │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   OpenAI API Call           │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Response Parser           │
│  - adapter.extract_tool_call│
└──────┬──────────────────────┘
       │
       ├─────────────────┬─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Tool Call   │  │ Final Answer│  │ Parse Error │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       ▼                │                │
┌─────────────────────┐ │                │
│ Tool Registry       │ │                │
│ _tool_map[tool_name]│ │                │
└──────┬──────────────┘ │                │
       │                │                │
       ▼                │                │
┌─────────────────────┐ │                │
│ Tool Execution      │ │                │
│ tool.run(**args)    │ │                │
└──────┬──────────────┘ │                │
       │                │                │
       ▼                │                │
┌─────────────────────┐ │                │
│ Format Result       │ │                │
│ {"role": "tool"}    │ │                │
└──────┬──────────────┘ │                │
       │                │                │
       └────────────────┴────────────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │ Update Memory       │
         │ memory.add(...)     │
         └─────────┬───────────┘
                   │
                   └──────► (Loop back or return)
```

### TinyCodeAgent Data Flow

```
┌─────────────┐
│  User Task  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│   MemoryManager             │
│  - SystemPromptStep         │
│  - TaskStep                 │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   LLM Request Builder       │
│  - messages = memory.to_msg │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   OpenAI API Call           │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Response Parser           │
│  - extract code block       │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   AST Validator             │
│  - check imports            │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Executor                  │
│  - run(code)                │
│  - namespace:               │
│    • tools                  │
│    • signals                │
│    • scratchpad             │
└──────┬──────────────────────┘
       │
       ├─────────────────┬─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ final_answer│  │ stdout      │  │ Error       │
│ called      │  │ captured    │  │ exception   │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       ▼                ▼                │
┌─────────────────────┐ │                │
│ Finalizer.set_answer│ │                │
└─────────────────────┘ │                │
                        │                │
       ┌────────────────┴────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Create ActionStep         │
│  - reasoning                │
│  - code                     │
│  - observation (stdout)     │
│  - signals                  │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   MemoryManager.add()       │
└──────┬──────────────────────┘
       │
       └──────► (Loop back or return)
```

---

## Memory Transformation Examples

### ReactAgent Memory Evolution

**Initial:**
```python
[
  {"role": "system", "content": "You are a helpful assistant"},
  {"role": "user", "content": "What's the weather in Tokyo?"}
]
```

**After tool call:**
```python
[
  {"role": "system", "content": "You are a helpful assistant"},
  {"role": "user", "content": "What's the weather in Tokyo?"},
  {"role": "assistant", "content": "I'll check the weather.", "tool_calls": [...]},
  {"role": "tool", "content": "72°F, sunny", "tool_call_id": "call_123"}
]
```

**After final answer:**
```python
[
  {"role": "system", "content": "You are a helpful assistant"},
  {"role": "user", "content": "What's the weather in Tokyo?"},
  {"role": "assistant", "content": "I'll check the weather.", "tool_calls": [...]},
  {"role": "tool", "content": "72°F, sunny", "tool_call_id": "call_123"},
  {"role": "assistant", "content": "The weather in Tokyo is 72°F and sunny."}
]
```

### TinyCodeAgent Memory Evolution

**Initial:**
```python
[
  SystemPromptStep(content="You are a coding assistant"),
  TaskStep(task="Read and analyze data.csv")
]
```

**After first iteration:**
```python
[
  SystemPromptStep(content="You are a coding assistant"),
  TaskStep(task="Read and analyze data.csv"),
  ActionStep(
    reasoning="I need to read the file first",
    code="data = read_file('data.csv')\nprint(data.head())",
    observation="  col1  col2\n0    1     4\n1    2     5",
    signals=[Signal(type="explore", message="Exploring data structure")]
  )
]
```

**After second iteration:**
```python
[
  SystemPromptStep(content="You are a coding assistant"),
  TaskStep(task="Read and analyze data.csv"),
  ActionStep(reasoning="I need to read the file first", ...),
  ActionStep(
    reasoning="I can see the data has 2 columns",
    code="store('columns', ['col1', 'col2'])\nfinal_answer('Analysis complete')",
    observation="Columns stored: ['col1', 'col2']",
    signals=[Signal(type="commit", message="Identified 2 columns")]
  )
]
```

---

## Performance Considerations

### Token Usage

**Memory Growth:**
- Each iteration adds messages to history
- Unchecked growth leads to:
  - Increased latency
  - Higher API costs
  - Context window overflow

**Mitigation Strategies:**

```python
# ReactAgent: Prune old messages
if len(memory) > 1000:
    # Keep system + last N messages
    memory = memory[:2] + memory[-500:]

# TinyCodeAgent: Prune ActionSteps
memory_manager.prune(strategy=prune_old_observations)
```

### Execution Overhead

**ReactAgent:**
- Minimal overhead
- Simple message list operations
- Fast tool lookups

**TinyCodeAgent:**
- AST parsing on each execution
- Namespace building
- stdout redirection
- Signal collection
- **Trade-off**: Richer execution model vs. performance

---

## Error Handling Flow

### ReactAgent Errors

```
Tool Call → Tool Execution → Exception → Error Message → Memory → LLM Retry
```

```python
try:
    result = await tool.run(**args)
except Exception as e:
    error_msg = f"Tool error: {str(e)}"
    memory.add("tool", error_msg, tool_call_id=call.id)
    # LLM sees error and can retry
```

### TinyCodeAgent Errors

```
Code Gen → AST Check → Execution → Exception → stdout → Memory → LLM Retry
```

```python
try:
    output = await executor.run(code)
except ExecutionTimeout:
    output = "Error: Code execution timed out"
except Exception as e:
    output = f"Error: {str(e)}"

# Error appears in stdout, added to observation
action_step = ActionStep(observation=output)
```

---

## Debugging Data Flow

### Instrumentation Points

1. **Pre-LLM:**
   ```python
   logger.debug(f"Messages: {messages}")
   logger.debug(f"Tools: {[t.name for t in tools]}")
   ```

2. **Post-LLM:**
   ```python
   logger.debug(f"Response: {response.model_dump()}")
   ```

3. **Execution:**
   ```python
   logger.debug(f"Tool call: {tool_call}")
   logger.debug(f"Code: {code}")
   ```

4. **Memory Update:**
   ```python
   logger.debug(f"Memory size: {len(memory)}")
   logger.debug(f"Last step: {memory[-1]}")
   ```

### Signal-Based Debugging

```python
# Collect signals for observability
def handle_signal(signal: Signal):
    if signal.type == "uncertain":
        logger.warning(f"Agent uncertain: {signal.message}")
    elif signal.type == "explore":
        logger.info(f"Agent exploring: {signal.message}")

set_signal_collector(handle_signal)
```

---

## Related Documentation

- **Agent Hierarchy**: `/docs/architecture/agent-hierarchy.md`
- **Design Patterns**: `/docs/architecture/design-patterns.md`
- **Memory Management**: `/docs/architecture/memory-management.md`
- **Tool Calling**: `/docs/architecture/tools/tool-calling-adapters.md`
- **Code Execution**: `/docs/architecture/code-execution.md`
