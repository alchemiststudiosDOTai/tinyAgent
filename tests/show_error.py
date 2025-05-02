#!/usr/bin/env python

import os
import sys
import pathlib
import json
import traceback

# Add the src directory to the path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from tinyagent.decorators import tool
from tinyagent.agent import tiny_agent
from tinyagent.exceptions import AgentRetryExceeded

@tool
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two integers."""
    return a + b

def main():
    """Show the exact error when using the calculate_sum tool for weather query."""
    # Create a basic agent
    agent = tiny_agent(tools=[calculate_sum])
    
    print("\n==== TRYING TEST ASSERTION ====")
    print("with pytest.raises(AgentRetryExceeded):")
    print("    agent.run(\"what is the weather like today?\")")
    print("\nBut actually we get:")
    
    # Try the weather query
    try:
        result = agent.run("what is the weather like today?")
        print(f"Result: {result}")
    except Exception as e:
        print(f"\n==== ERROR TYPE: {type(e).__name__} ====")
        print(f"ERROR MESSAGE: {str(e)}")
        
        # If it's AgentRetryExceeded, show the retry history
        if isinstance(e, AgentRetryExceeded):
            print("\n==== RETRY HISTORY ====")
            for i, attempt in enumerate(e.history):
                print(f"\nAttempt {i+1}:")
                print(f"  Model: {attempt.get('model')}")
                print(f"  Temperature: {attempt.get('temperature')}")
                print(f"  Error: {attempt.get('error')}")
                
        print("\n==== FULL TRACEBACK ====")
        traceback.print_exc()
    
    # Now try with config that disables structured outputs
    print("\n\n==== TRYING WITH structured_outputs=False ====")
    fixed_agent = tiny_agent(tools=[calculate_sum])
    
    try:
        result = fixed_agent.run("what is the weather like today?")
        print(f"Result: {result}")
    except Exception as e:
        print(f"\n==== ERROR TYPE: {type(e).__name__} ====")
        print(f"ERROR MESSAGE: {str(e)}")
        
        if isinstance(e, AgentRetryExceeded):
            print("\n==== RETRY HISTORY ====")
            for i, attempt in enumerate(e.history):
                print(f"\nAttempt {i+1}:")
                print(f"  Model: {attempt.get('model')}")
                print(f"  Temperature: {attempt.get('temperature')}")
                print(f"  Error: {attempt.get('error')}")
                
        print("\n==== FULL TRACEBACK ====")
        traceback.print_exc()

if __name__ == "__main__":
    main() 