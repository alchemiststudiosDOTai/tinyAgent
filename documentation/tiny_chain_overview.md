# tiny_chain Overview

## Simple Explanation

**What is `tiny_chain`?**  
`tiny_chain` is a system that helps an AI agent decide which tools to use (and in what order) to solve a user's request.

**How does it work?**  
When you give it a task, it first asks a "triage agent" (powered by an LLM) to suggest a plan. The plan might be to use one tool, or several tools in sequence.

**What if the plan fails?**  
If the triage agent can't make a good plan, `tiny_chain` just tries all the tools it has, one after another, to make sure something useful happens.

**Why is this useful?**  
It lets the AI agent handle complex tasks by chaining together multiple tools, and it's robust to errors or unexpected LLM output.

---

## Technical Detail

### Initialization

- `tiny_chain` is a singleton class that manages tasks and agents.
- On creation, it registers all available tools and creates a special "triage agent" with access to all tools.

### Task Handling

- When a new task is submitted, it is assigned a unique ID and stored.
- The `_run_with_triage` method is called to ask the triage agent for a plan.
  - The triage agent is prompted with the task and a list of tools.
  - It is expected to return a JSON plan (either a single tool call or a sequence).
  - If the response is invalid, it retries up to `max_retries` times.

### Tool Execution

- If the triage agent returns a valid plan:
  - If it's a single tool, `_execute_single_tool` runs it.
  - If it's a sequence, `_execute_tool_sequence` runs each tool in order, passing results as needed.
- If the triage agent fails, `_use_all_tools_fallback` runs all tools in sequence as a fallback.

### Failure Handling

- All exceptions and errors are caught and logged.
- If all attempts fail, the task is marked as failed and an error message is stored.

### Extensibility

- New tools can be registered easily.
- The triage agent can be improved or replaced to support more complex planning.

---

## Example Task Flow

1. **User submits a query:**
   - e.g., "Find current US import tariffs and summarize the results."
2. **Triage agent is called:**
   - Returns a plan: use search tool → browser tool → summarizer.
3. **tiny_chain executes the plan:**
   - Each tool is run in order, results are chained.
4. **If triage fails:**
   - All tools are run in sequence as a fallback.

---

## Summary

`tiny_chain` provides a robust, flexible way to chain together multiple tools for complex AI tasks. It uses a triage agent to plan intelligently, but always has a fallback to ensure tasks are attempted even if the LLM output is unexpected. This makes it both powerful and reliable for orchestrating tool-based AI workflows.
