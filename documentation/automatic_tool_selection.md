# Automatic Tool Selection in tinyAgent

## Simple Explanation

The **Automatic Tool Selection** feature in tinyAgent lets you create agents that automatically pick and use the right tools for a task - just like a smart assistant that knows which tool to use without being told explicitly.

### Quick Example

```python
from orchestrator2 import Orchestrator2
from tinyagent.tools.duckduckgo_search import duckduckgo_search_tool

# Create orchestrator with tools
orchestrator = Orchestrator2.get_instance(tools=[duckduckgo_search_tool])

# Submit a task in plain English
task_id = orchestrator.submit_task("what is the weather in New York?")
```

## How It Works

1. **Tool Registration**

   - Tools are registered with the orchestrator
   - Each tool has a name, description, and function
   - Tools can be built-in or custom-made

2. **Task Analysis**

   - When you submit a task, the orchestrator analyzes it
   - It looks at what the task is asking for
   - It matches the task to available tools

3. **Automatic Selection**
   - The orchestrator picks the best tool for the job
   - No need to specify which tool to use
   - Multiple tools can be chained together if needed

## Real-World Example

Here's what happens in our weather search example:

```
Query: "what is the weather in New York?"
↓
Orchestrator analyzes query
↓
Recognizes it needs weather information
↓
Automatically selects DuckDuckGo search tool
↓
Returns formatted weather results
```

### Sample Output

```
Tools used: duckduckgo_search

Search Results:

1. 10-Day Weather Forecast for New York, NY
   Be prepared with the most accurate 10-day forecast...

2. New York, NY Weather Forecast
   Current conditions, wind, air quality...

3. Manhattan, NY Weather
   Today's and tonight's weather forecast...
```

## Best Practices

1. **Natural Language Queries**

   - Write queries in plain English
   - Be specific about what you want
   - Don't worry about tool names or syntax

2. **Tool Registration**

   - Register tools that complement each other
   - Tools should have clear descriptions
   - Keep tool functions focused and specific

3. **Error Handling**
   - Check task status for errors
   - Handle cases where no suitable tool is found
   - Format results for readability

## Behind the Scenes

The orchestrator uses several components:

- **Triage Agent**: Analyzes tasks and picks tools
- **Tool Chain**: Executes multiple tools if needed
- **Result Formatter**: Makes output readable
- **Error Handler**: Manages failures gracefully

## Common Use Cases

1. **Web Searches**

   - Finding current information
   - Research queries
   - News updates

2. **Data Processing**

   - Formatting results
   - Filtering information
   - Combining data sources

3. **Task Automation**
   - Chaining multiple tools
   - Processing sequences
   - Complex workflows

## Summary

Automatic tool selection makes tinyAgent more intuitive by:

- Understanding natural language
- Picking appropriate tools automatically
- Chaining tools when needed
- Formatting results clearly

This removes the need to know tool details and lets you focus on what you want to achieve rather than how to achieve it.
