#!/usr/bin/env python3
"""
Example 5: Elder Brain Orchestration Demo (Runnable)

This example demonstrates how to use the ElderBrain meta-agent to analyze a complex task,
gather information, select relevant tools, and execute them dynamically.

It performs:
1. Information Gathering (via LLM)
2. Tool Selection (based on LLM output)
3. Real Tool Execution (calls available tools)
"""

import os
import sys
import json

# Add parent directory to the path so we can import the core package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.factory.orchestrator import Orchestrator
from core.factory.elder_brain import ElderBrain

def main():
    # Initialize orchestrator
    orchestrator = Orchestrator.get_instance()

    # Create ElderBrain
    elder_brain = ElderBrain(orchestrator)

    # Define a complex task
    task_description = "Research the latest AI trends and generate a detailed report with code examples."

    print("\n===== ELDER BRAIN DEMO =====")
    print(f"Task: {task_description}\n")

    # Phase 1: Information Gathering
    info = elder_brain.gather_information(task_description)
    print("\n--- Information Gathering Result ---")
    print(json.dumps(info, indent=2))

    # Extract recommended tools from info
    recommended_tools = info.get("recommended_tools", [])
    if not recommended_tools:
        print("\nNo recommended tools found. Using default 'chat' tool.")
        recommended_tools = ["chat"]

    # Phase 2 & 3: Execute recommended tools
    print("\n===== EXECUTING RECOMMENDED TOOLS =====")
    for tool_name in recommended_tools:
        print(f"\n--- Executing tool: {tool_name} ---")
        try:
            # Submit the task to the orchestrator with tool hint
            task_id = orchestrator.submit_task(
                task_description,
                preferred_tool=tool_name
            )
            status = orchestrator.get_task_status(task_id)
            print(f"Result from {tool_name}:")
            print(status.result)
        except Exception as e:
            print(f"Error executing tool '{tool_name}': {e}")

    print("\n===== ELDER BRAIN DEMO COMPLETE =====")

if __name__ == "__main__":
    main()