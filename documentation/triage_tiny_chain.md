# tinyAgent tiny_chain Deep Dive

## Overview

The tiny_chain is the central nervous system of tinyAgent. It manages task execution, tool selection, and agent coordination. Think of it as a smart project manager that:

- Understands natural language tasks
- Picks the right tools for the job
- Coordinates between different agents
- Handles errors and retries
- Manages task state and results

## Core Components

### 1. Triage Agent

```python
# Internal creation of triage agent
triage_agent = factory.create_agent(
    tools=list(factory.list_tools().values()),
    model=model
)
```

The triage agent is a specialized agent that:

- Has access to ALL registered tools
- Analyzes incoming tasks
- Decides execution strategy
- Can create new agents if needed

### 2. Task Management

```python
# Task submission
task_id = tiny_chain.submit_task("analyze this code")
status = tiny_chain.get_task_status(task_id)
```

Tasks are managed through:

- Unique task IDs
- Status tracking
- Result storage
- Error handling

### 3. Tool Registry

```python
# Tool registration
factory.register_tool(duckduckgo_search_tool)
factory.register_tool(custom_tool)
```

The tool registry:

- Maintains available tools
- Handles tool metadata
- Manages tool dependencies
- Enables dynamic tool loading

## Task Flow

1. **Task Submission**

   ```python
   task_id = tiny_chain.submit_task(
       "what is the weather in New York?",
       need_permission=False
   )
   ```

   - Task is received
   - ID is assigned
   - Initial state is set

2. **Triage Analysis**

   ```python
   assessment = {
       "assessment": "direct",  # or "phased", "create_new"
       "requires_new_agent": False,
       "reasoning": "Can handle with existing search tool"
   }
   ```

   - Task is analyzed
   - Execution path is determined
   - Tool requirements are identified

3. **Execution Paths**

   a. **Direct Execution**

   ```python
   # Single tool execution
   result = tool.execute(args)
   ```

   b. **Tool Chain**

   ```python
   # Multiple tools in sequence
   chain = [
       {"tool": "search", "args": {...}},
       {"tool": "process", "args": {...}}
   ]
   ```

   c. **New Agent Creation**

   ```python
   # When specialized agent is needed
   new_agent = factory.create_agent(
       tools=[required_tools],
       description="Purpose of new agent"
   )
   ```

4. **Result Processing**
   ```python
   # Result formatting
   formatted_result = {
       "success": True,
       "data": processed_data,
       "tools_used": ["tool1", "tool2"]
   }
   ```

## Advanced Features

### 1. Permission Management

```python
# Permission check
if task.needs_permission:
    await_permission()
    if permission_granted:
        proceed()
```

### 2. Retry Mechanism

```python
class RetryManager:
    def next_attempt(self):
        # Increase temperature
        # Possibly switch model
        return new_temp, new_model
```

### 3. Tool Chain Optimization

```python
# Chain optimization
optimized_chain = [
    tool for tool in chain
    if tool.is_necessary()
]
```

### 4. Error Recovery

```python
try:
    result = execute_chain(tools)
except Exception:
    fallback_result = execute_fallback()
```

## State Management

### 1. Task States

- `PENDING`: Initial state
- `ANALYZING`: Under triage
- `EXECUTING`: Running tools
- `AWAITING_PERMISSION`: Needs approval
- `COMPLETED`: Task finished
- `FAILED`: Error occurred

### 2. Result Types

```python
class TaskResult:
    success: bool
    data: Any
    error: Optional[str]
    tools_used: List[str]
    execution_time: float
```

## Best Practices

### 1. Task Submission

```python
# Good
task_id = tiny_chain.submit_task(
    "find python code examples about sorting",
    context={"language": "python", "topic": "sorting"}
)

# Bad - too vague
task_id = tiny_chain.submit_task("find stuff")
```

### 2. Tool Registration

```python
# Good
tool = Tool(
    name="search",
    description="Searches for specific information",
    parameters={"query": "Search query", "limit": "Result limit"}
)

# Bad - vague description, missing parameters
tool = Tool(name="search", description="Searches")
```

### 3. Error Handling

```python
# Good
try:
    result = tiny_chain.execute_task(task_id)
    if result.error:
        handle_error(result.error)
except OrchestratorError as e:
    log_error(e)
    notify_admin(e)
```

### 4. Tool Chain Design

```python
# Good: Logical tool progression
tools = [
    search_tool,      # Find information
    browser_tool,     # Verify and expand
    process_tool,     # Process data
    summarize_tool    # Create summary
]

# Bad: Illogical tool order
tools = [
    summarize_tool,   # Nothing to summarize yet
    search_tool,      # Search after summary?
    browser_tool      # Browse after summary?
]
```

## Common Patterns

### 1. Multi-Step Tasks

```python
# Research task
task_id = tiny_chain.submit_task("""
1. Search for recent AI developments
2. Analyze the findings
3. Generate a summary report
""")
```

### 2. Tool Chaining

```python
# Chain tools automatically
search_result = search_tool.execute(query)
processed = process_tool.execute(search_result)
final = format_tool.execute(processed)
```

### 3. Context Preservation

```python
# Maintain context across tools
context = {
    "original_query": query,
    "previous_results": [],
    "user_preferences": preferences
}
```

## Debugging

### 1. Logging

```python
logger.info("Task received: %s", task_id)
logger.debug("Tool selection: %s", selected_tools)
logger.error("Execution failed: %s", error)
```

### 2. Status Inspection

```python
status = tiny_chain.get_task_status(task_id)
print(f"State: {status.state}")
print(f"Progress: {status.progress}")
print(f"Tools used: {status.tools_used}")
```

## Tool Chain Integration

### 1. Basic Tool Chain

```python
# Initialize tools
search_tool = get_search_tool()
browser_tool = get_browser_tool()
summarize_tool = get_summarize_tool()

# Register with tiny_chain
chain = tiny_chain.get_instance(
    tools=[search_tool, browser_tool, summarize_tool]
)
```

### 2. Automated Chain Execution

```python
# The chain will automatically:
# 1. Search for information
# 2. Browse relevant pages
# 3. Summarize findings
task_id = chain.submit_task(
    "research US import tariffs and summarize findings"
)
```

### 3. Result Processing

```python
status = chain.get_task_status(task_id)
if status.error:
    handle_error(status.error)
else:
    # Access step-by-step results
    for step in status.result['steps']:
        tool_name = step['tool']
        tool_result = step['result']
        process_step_result(tool_name, tool_result)
```

## Real-World Examples

### 1. Tariff Research Tool

```python
@tool(
    name="summarize",
    description="Summarize input text using the LLM"
)
def summarize_text(text: str) -> str:
    llm = get_llm()
    prompt = (
        "Summarize the following text:\n\n"
        f"{text}\n\n"
        "Summary:"
    )
    return llm(prompt).strip()

# Tool chain setup
chain = tiny_chain.get_instance(
    tools=[
        search_tool,
        browser_tool,
        summarize_text._tool
    ]
)

# Execute research
task_id = chain.submit_task(
    "Find current US import tariffs and use the browser "
    "to visit official trade websites to get details"
)
```

### 2. Result Inspection

```python
def print_step(step_num: int, step_data: dict) -> None:
    print(f"\n=== Step {step_num} ===")
    if isinstance(step_data, dict):
        print(f"Tool Used: {step_data.get('tool', 'Unknown')}")
        print("\nInput:", json.dumps(step_data.get('input', {}), indent=2))
        print("\nResult:", json.dumps(step_data.get('result', {}), indent=2))
```

## Integration Patterns

### 1. Tool Registration Pattern

```python
# Good: Register related tools together
chain = tiny_chain.get_instance(
    tools=[
        search_tool,    # Information gathering
        browser_tool,   # Deep inspection
        summarize_tool  # Result processing
    ]
)

# Bad: Missing essential tools
chain = tiny_chain.get_instance(
    tools=[search_tool]  # Can't process or analyze results
)
```

### 2. Task Submission Pattern

```python
# Good: Clear, specific task with context
task_id = chain.submit_task(
    "Find import tariffs for electronics from China",
    context={
        "category": "electronics",
        "country": "China",
        "type": "import"
    }
)

# Bad: Vague task without context
task_id = chain.submit_task("find tariffs")
```

### 3. Result Processing Pattern

```python
# Good: Structured result handling
status = chain.get_task_status(task_id)
if status.error:
    log_error(status.error)
    notify_admin(status.error)
else:
    for step in status.result['steps']:
        validate_step_result(step)
        store_step_data(step)
        update_metrics(step)
```

## Summary

The tiny_chain provides:

- Intelligent task management
- Automatic tool selection
- Flexible execution paths
- Robust error handling
- Clear status tracking

This makes it the ideal system for:

- Complex task automation
- Tool chain management
- Dynamic agent creation
- Result processing and formatting
