#!/usr/bin/env python3
"""
Example 1: Basic Agent Creation

This example shows the simplest way to create a TinyAgent with minimal configuration.
"""

import os
import sys

# Add parent directory to the path so we can import the core package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import Agent
from core.factory.agent_factory import AgentFactory
from core.factory.orchestrator import Orchestrator
from core.logging import get_logger

logger = get_logger(__name__)

def main():
    """Create and run a basic agent with a simple calculator tool."""
    # Initialize the orchestrator
    orchestrator = Orchestrator.get_instance()
    
    # Example query
    query = "Calculate 5 + 3"
    print(f"Running agent with query: '{query}'")
    
    # Submit the task
    task_id = orchestrator.submit_task(query)
    
    # Get the result
    task_status = orchestrator.get_task_status(task_id)
    
    # Print the result
    print(f"\nResult: {task_status.result}")


def calculate(operation: str, a: float, b: float) -> float:
    """Calculator tool implementation."""
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else ValueError("Cannot divide by zero")
    }
    
    if operation not in operations:
        raise ValueError(f"Unknown operation: {operation}. Valid operations are: {', '.join(operations.keys())}")
    
    result = operations[operation](a, b)
    if isinstance(result, ValueError):
        raise result
    return result


if __name__ == "__main__":
    main()
