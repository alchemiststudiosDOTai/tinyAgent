#!/usr/bin/env python3
"""
Simple ReAct Example - Phase 1: Basic Setup with One Tool

This example shows the minimal setup for a ReAct agent with a single tool.
"""

import json
from dotenv import load_dotenv
from tinyagent.react.react_agent import ReActAgent
from tinyagent.decorators import tool

# Load environment variables
load_dotenv()

# Create a simple calculator tool
@tool
def add_numbers(a: float, b: float) -> float:
    """Add two numbers together."""
    result = a + b
    print(f"[Tool Execution] add_numbers({a}, {b}) = {result}")
    return result

def main():
    print("=== Simple ReAct Agent Setup ===\n")
    
    # Phase 1: Basic setup
    # 1. Create the agent
    agent = ReActAgent()
    
    # 2. Register our tool
    # The @tool decorator creates a Tool instance at function._tool
    agent.register_tool(add_numbers._tool)
    
    print(f"Registered tools: {list(agent.tools.keys())}")
    
    # 3. Create a simple LLM callable for testing
    # In phase 2, we'll integrate with the real LLM
    def test_llm(prompt: str) -> str:
        print(f"\n[LLM Prompt]:\n{prompt}\n")
        
        # For now, return a hardcoded response that uses our tool
        response = json.dumps({
            "thought": "I need to add 5 and 3",
            "action": {()
                "tool": "add_numbers",
                "args": {"a": 5, "b": 3}
            }
        })
        print(f"[LLM Response]: {response}\n")
        return response
    
    # 4. Run the agent with a simple query
    query = "What is 5 plus 3?"
    print(f"Query: {query}")
    
    result = agent.run_react(
        query=query,
        llm_callable=test_llm,
        max_steps=1  # Just one step for this test
    )
    
    print(f"\nResult: {result}")
    
    # Show what happened
    print("\n=== What Happened ===")
    print("1. Agent received query")
    print("2. Agent built prompt with ReAct instructions")
    print("3. LLM returned JSON with thought and action")
    print("4. Agent executed the add_numbers tool with args")
    print("5. Tool returned result: 8")
    print("\nNext phase:  Integrate with real LLM")

if __name__ == "__main__":
    main()
