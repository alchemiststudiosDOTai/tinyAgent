"""Test console tracing output."""

import sys
from pathlib import Path
import logging

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from tinyagent.agent import tiny_agent
from tinyagent.decorators import tool
from tinyagent.observability.tracer import configure_tracing

# Set up logging to see console output
logging.basicConfig(level=logging.INFO)

@tool
def simple_test(message: str) -> str:
    """A simple test tool."""
    return f"Test tool received: {message}"

def main():
    # Configure tracing (this will use settings from config.yml)
    configure_tracing()
    
    # Create an agent with tracing enabled
    agent = tiny_agent(tools=[simple_test], trace_this_agent=True)
    
    # Run the agent - this should produce console output for the trace
    result = agent.run("Use simple_test tool with the message 'Hello, Tracing!'")
    print("\nAgent result:", result)

if __name__ == "__main__":
    main() 