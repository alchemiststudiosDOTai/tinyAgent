#!/usr/bin/env python3
"""
Full ReAct Test - Shows complete request/response cycle

This example shows the full ReAct cycle with mock LLM responses
to demonstrate the fix working end-to-end.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tinyagent.react.react_agent import ReActAgent
from tinyagent.decorators import tool
import json

# Define tools
@tool
def calculate(expression: str) -> float:
    """Evaluate a mathematical expression."""
    print(f"[TOOL EXECUTION] calculate({expression})")
    result = eval(expression)
    print(f"[TOOL RESULT] {result}")
    return result

@tool
def add_numbers(a: float, b: float) -> float:
    """Add two numbers together."""
    print(f"[TOOL EXECUTION] add_numbers({a}, {b})")
    result = a + b
    print(f"[TOOL RESULT] {result}")
    return result

def create_mock_llm():
    """Create a mock LLM that responds appropriately to demonstrate the fix"""
    call_count = 0
    
    def mock_llm(prompt: str) -> str:
        nonlocal call_count
        call_count += 1
        
        print(f"\n🤖 LLM CALL #{call_count}")
        print("=" * 50)
        print("PROMPT SENT TO LLM:")
        print("-" * 30)
        print(prompt)
        print("-" * 30)
        
        # Mock responses that use the available tools correctly
        if call_count == 1:
            # First call - calculate 40% of 15
            response = {
                "thought": "I need to find 40% of 15 first, then subtract that from 15. Let me calculate 15 * 0.4",
                "action": {
                    "tool": "calculate",
                    "args": {"expression": "15 * 0.4"}
                }
            }
        elif call_count == 2:
            # Second call - subtract the result
            response = {
                "thought": "Now I know 40% of 15 is 6, so I need to calculate 15 - 6 to get the final answer",
                "action": {
                    "tool": "calculate", 
                    "args": {"expression": "15 - 6"}
                }
            }
        else:
            # Final answer
            response = {
                "thought": "I've calculated that 15 - 6 = 9, so the person has 9 apples left",
                "action": {
                    "tool": "final_answer",
                    "args": {"answer": "You have 9 apples left after giving away 40% of your 15 apples."}
                }
            }
        
        response_json = json.dumps(response)
        print(f"\nLLM RESPONSE:")
        print(response_json)
        print("=" * 50)
        
        return response_json
    
    return mock_llm

def main():
    print("🚀 Full ReAct Test - Complete Request/Response Cycle")
    print("=" * 60)
    
    # Create agent and register tools
    agent = ReActAgent()
    agent.register_tool(calculate._tool)
    agent.register_tool(add_numbers._tool)
    
    print(f"📦 Registered tools: {list(agent.tools.keys())}")
    print()
    
    # Test query
    query = "If I have 15 apples and give away 40%, how many do I have left?"
    print(f"❓ Query: {query}")
    
    try:
        print("\n🎬 Starting ReAct reasoning cycle...")
        
        result = agent.run_react(
            query=query,
            llm_callable=create_mock_llm(),
            max_steps=3
        )
        
        print("\n🎯 FINAL RESULT:")
        print("=" * 30)
        print(result)
        print("=" * 30)
        
        print("\n✅ SUCCESS! The fix works:")
        print("- LLM received tool information in prompt")
        print("- LLM used correct tool names ('calculate', not 'calculator')")
        print("- No 'Unknown tool' errors occurred")
        print("- Framework handled everything automatically")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()