#!/usr/bin/env python3
"""
Example: Tariff Research Tool

This example demonstrates using the orchestrator to automatically chain
search and browser tools for researching tariff information.
"""

import os
import json
import sys

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