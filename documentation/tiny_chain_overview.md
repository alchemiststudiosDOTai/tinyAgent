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

## Example: Automated Tariff Research Tool

Below is a complete example of how to use `tiny_chain` to automatically chain together search, browsing, and summarization tools for a real-world research task.

```python
import json
from tinyagent.factory.tiny_chain import tiny_chain
from tinyagent.tools.duckduckgo_search import get_tool as get_search_tool
from tinyagent.tools.custom_text_browser import get_tool as get_browser_tool
from tinyagent.decorators import tool
from tinyagent.agent import get_llm

# Tool: Summarize text using the LLM
@tool(
    name="summarize",
    description="Summarize input text using the LLM"
)
def summarize_text(text: str) -> str:
    llm = get_llm()
    prompt = (
        "Summarize the following text in a concise and clear manner:\n\n"
        f"{text}\n\n"
        "Summary:"
    )
    return llm(prompt).strip()

# Utility: Pretty-print each step in the tool chain
def print_step(step_num: int, step_data: dict) -> None:
    print(f"\n=== Step {step_num} ===")
    if isinstance(step_data, dict):
        if 'tool' in step_data:
            print(f"Tool Used: {step_data['tool']}")
        if 'input' in step_data:
            print("\nInput:")
            print(json.dumps(step_data['input'], indent=2))
        if 'result' in step_data:
            print("\nResult:")
            print(json.dumps(step_data['result'], indent=2))
    print("=" * 60)

# Main: Run the research workflow
if __name__ == "__main__":
    # Initialize tools
    search_tool = get_search_tool()
    browser_tool = get_browser_tool()

    # Set up orchestrator with all tools
    orchestrator = tiny_chain.get_instance([
        search_tool,
        browser_tool,
        summarize_text._tool
    ])

    # Example research query
    query = (
        "Find current US import tariffs and use the browser to visit official trade websites to get details."
    )

    print("=" * 60)
    print("Tariff Research Tool Example")
    print("=" * 60)
    print(f"\nResearching: '{query}'\n" + "-" * 60)

    try:
        task_id = orchestrator.submit_task(query)
        status = orchestrator.get_task_status(task_id)

        if status.error:
            print(f"Error: {status.error}")
        elif isinstance(status.result, dict):
            # Show each step in the tool chain
            if 'steps' in status.result:
                print("\nTool Chain Steps:")
                for i, step in enumerate(status.result['steps'], 1):
                    print_step(i, step)
            # Show summary of tools used
            if 'tools_used' in status.result:
                print("\nTools Used in Order:")
                for tool in status.result['tools_used']:
                    print(f"- {tool}")
        print("-" * 60)
    except Exception as e:
        print(f"Error: {e}")

---

This example demonstrates how `tiny_chain` can orchestrate multiple tools to solve a complex research task, providing both step-by-step output and a summary of the tools used.


#!/usr/bin/env python3
"""
Example: Tariff Research Tool

This example demonstrates using the orchestrator to automatically chain
search and browser tools for researching tariff information.
"""

import json

from tinyagent.factory.tiny_chain import tiny_chain
from tinyagent.tools.duckduckgo_search import get_tool as get_search_tool
from tinyagent.tools.custom_text_browser import get_tool as get_browser_tool
from tinyagent.decorators import tool
from tinyagent.agent import get_llm


@tool(
    name="summarize",
    description="Summarize input text using the LLM"
)
def summarize_text(text: str) -> str:
    """
    Summarize the provided text using the LLM.

    Args:
        text (str): The text to summarize.

    Returns:
        str: The summary of the input text.
    """
    llm = get_llm()
    prompt = (
        "Summarize the following text in a concise and clear manner:\n\n"
        f"{text}\n\n"
        "Summary:"
    )
    summary = llm(prompt)
    return summary.strip()


def print_step(step_num: int, step_data: dict) -> None:
    """
    Print details about a step in the tool chain.
    
    Args:
        step_num (int): The step number in the sequence
        step_data (dict): Data containing tool execution details
    """
    print(f"\n=== Step {step_num} ===")
    
    if isinstance(step_data, dict):
        if 'tool' in step_data:
            print(f"Tool Used: {step_data['tool']}")
        
        if 'input' in step_data:
            print("\nInput:")
            print(json.dumps(step_data['input'], indent=2))
        
        if 'result' in step_data:
            print("\nResult:")
            print(json.dumps(step_data['result'], indent=2))
    
    print("=" * 60)


def main() -> None:
    """Create an agent that researches tariff information."""
    # Initialize tools
    search_tool = get_search_tool()
    browser_tool = get_browser_tool()
    
    # Set up orchestrator with tools
    orchestrator = tiny_chain.get_instance(
        tools=[
            search_tool,
            browser_tool,
            summarize_text._tool
        ]
    )

    # Define research queries
    queries = [
        "Find current US import tariffs and use the browser to visit official trade websites to get details",
    ]

    # Print header
    print("=" * 60)
    print("Tariff Research Tool")
    print("=" * 60)

    # Process each query
    for query in queries:
        print(f"\nResearching: '{query}'")
        print("-" * 60)

        try:
            task_id = orchestrator.submit_task(query)
            status = orchestrator.get_task_status(task_id)

            if status.error:
                print(f"Error: {status.error}")
            elif isinstance(status.result, dict):
                # Print tool chain steps
                if 'steps' in status.result:
                    print("\nTool Chain Steps:")
                    for i, step in enumerate(status.result['steps'], 1):
                        print_step(i, step)
                
                # Print tools used summary
                if 'tools_used' in status.result:
                    print("\nTools Used in Order:")
                    for tool in status.result['tools_used']:
                        print(f"- {tool}")
            
            print("-" * 60)
        
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main() 