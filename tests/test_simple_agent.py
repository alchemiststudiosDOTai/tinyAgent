#!/usr/bin/env python

import os
import sys
import pathlib
import json

# Add the src directory to the path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from tinyagent.decorators import tool
from tinyagent.agent import tiny_agent

@tool
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two integers."""
    return a + b

def test_agent(model_name):
    """Test the agent with a specific model."""
    print(f"\n----- Testing with model: {model_name} -----")
    
    # Create agent with specified model
    agent = tiny_agent(tools=[calculate_sum], model=model_name)
    
    # Test with a simple query that should work
    test_query = "add 5 and 3"
    print(f"Query: '{test_query}'")
    
    try:
        result = agent.run(test_query, expected_type=int)
        print(f"SUCCESS: Result = {result}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")

def main():
    """Test the agent with different models."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set in environment")
        return
    
    print(f"Using API key: {api_key[:5]}...{api_key[-5:]}")
    
    # Test with different model variants
    test_agent("deepseek/deepseek-chat")
    test_agent("deepseek/deepseek-coder")
    test_agent("anthropic/claude-3-sonnet")
    test_agent("anthropic/claude-3-haiku")
    
if __name__ == "__main__":
    main() 