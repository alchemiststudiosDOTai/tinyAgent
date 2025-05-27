#!/usr/bin/env python3
"""
Fixed ReAct Example - Shows the tool discovery fix in action

This example demonstrates that the ReAct agent now automatically 
includes tool information in prompts, fixing the "Unknown tool" error.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
from tinyagent.react.react_agent import ReActAgent
from tinyagent.decorators import tool
from tinyagent.agent import get_llm

# Load environment variables
load_dotenv()

# Define tools - any function name works now!
@tool
def calculate(expression: str) -> float:
    """Evaluate a mathematical expression."""
    print(f"[TOOL EXECUTION] calculate({expression})")
    try:
        result = eval(expression)
        print(f"[TOOL RESULT] {result}")
        return result
    except Exception as e:
        print(f"[TOOL ERROR] {e}")
        return f"Error: {e}"

@tool
def add_numbers(a: float, b: float) -> float:
    """Add two numbers together."""
    print(f"[TOOL EXECUTION] add_numbers({a}, {b})")
    result = a + b
    print(f"[TOOL RESULT] {result}")
    return result

def main():
    print("🚀 Fixed ReAct Agent Example")
    print("=" * 50)
    
    # Create agent and register tools
    agent = ReActAgent()
    agent.register_tool(calculate._tool)
    agent.register_tool(add_numbers._tool)
    
    print(f"📦 Registered tools: {list(agent.tools.keys())}")
    print()
    
    # Test the fix with the same query that was failing
    query = "If I have 15 apples and give away 40%, how many do I have left?"
    print(f"❓ Query: {query}")
    print()
    
    try:
        print("🤖 Starting ReAct reasoning with REAL LLM...")
        print("-" * 40)
        
        result = agent.run_react(
            query=query,
            llm_callable=get_llm(),
            max_steps=5
        )
        
        print("-" * 40)
        print(f"✅ REAL LLM Final Answer: {result}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("🔧 What was fixed:")
    print("- ReAct agent now automatically tells LLM about available tools")
    print("- No more 'Unknown tool' errors")
    print("- No need to manually enhance prompts")
    print("- Framework handles tool discovery properly")

if __name__ == "__main__":
    main()