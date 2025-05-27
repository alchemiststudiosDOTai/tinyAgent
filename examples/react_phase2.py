#!/usr/bin/env python3
"""
ReAct Example - Phase 2: Integration with Real LLM

This example shows how to use the ReAct agent with TinyAgent's real LLM
using the robust JSON parser and better step visualization.
"""

import json
from dotenv import load_dotenv
from tinyagent.react.react_agent import ReActAgent
from tinyagent.decorators import tool
from tinyagent.agent import get_llm
from tinyagent.utils.json_parser import robust_json_parse

# Load environment variables
load_dotenv()

# Create our tools
@tool
def add_numbers(a: float, b: float) -> float:
    """Add two numbers together."""
    result = a + b
    print(f"\n[Tool Execution] add_numbers({a}, {b}) = {result}")
    return result

@tool
def multiply_numbers(a: float, b: float) -> float:
    """Multiply two numbers."""
    result = a * b
    print(f"\n[Tool Execution] multiply_numbers({a}, {b}) = {result}")
    return result

def create_react_llm():
    """Create an LLM wrapper for ReAct that ensures JSON responses."""
    # Get the base LLM from tinyagent
    base_llm = get_llm()
    
    # Track step count for better visualization
    step_count = 0
    
    def react_llm_wrapper(prompt: str) -> str:
        nonlocal step_count
        step_count += 1
        
        # Enhance the prompt to ensure proper JSON response
        enhanced_prompt = prompt + """

AVAILABLE TOOLS:
- add_numbers: Takes args {"a": number, "b": number}
- multiply_numbers: Takes args {"a": number, "b": number}

IMPORTANT: Respond with ONLY valid JSON, no other text or formatting.
Expected format: {"thought": "your reasoning", "action": {"tool": "tool_name", "args": {...}}}
For final answer: {"thought": "your conclusion", "action": {"tool": "final_answer", "args": {"answer": "your answer"}}}
"""
        
        print(f"\n{'='*60}")
        print(f"STEP {step_count} - LLM CALL")
        print(f"{'='*60}")
        
        # Show scratchpad if it exists
        if "Previous steps:" in prompt:
            lines = prompt.split('\n')
            for i, line in enumerate(lines):
                if line.strip() == "Previous steps:":
                    print("\n📝 SCRATCHPAD:")
                    j = i + 1
                    while j < len(lines) and lines[j].strip().startswith(('Thought:', 'Action:', 'Observation:')):
                        if lines[j].strip().startswith('Thought:'):
                            print(f"  💭 {lines[j].strip()}")
                        elif lines[j].strip().startswith('Action:'):
                            print(f"  🔧 {lines[j].strip()}")
                        elif lines[j].strip().startswith('Observation:'):
                            print(f"  👁️  {lines[j].strip()}")
                        j += 1
                    break
        
        # Extract and show the user query
        if "User query:" in prompt:
            query_line = prompt.split("User query:")[1].split("\n")[0].strip()
            print(f"\n📌 USER QUERY: {query_line}")
        
        print(f"\n⏳ Calling LLM...")
        
        # Call the real LLM
        response = base_llm(enhanced_prompt)
        
        print(f"\n📥 LLM RESPONSE:")
        print(f"{response[:500]}{'...' if len(response) > 500 else ''}")
        
        # Use the robust JSON parser
        parsed_json = robust_json_parse(response, expected_keys=['thought', 'action'])
        
        if parsed_json:
            # Successfully parsed, return as JSON string
            json_str = json.dumps(parsed_json)
            print(f"\n✅ PARSED JSON:")
            print(f"  💭 Thought: {parsed_json.get('thought', 'N/A')}")
            action = parsed_json.get('action', {})
            print(f"  🔧 Action: {action.get('tool', 'N/A')}")
            if action.get('args'):
                print(f"  📋 Args: {action.get('args')}")
            return json_str
        else:
            # Parsing failed, create fallback
            print("\n⚠️  JSON parsing failed, creating fallback response")
            fallback = {
                "thought": "Unable to parse LLM response properly",
                "action": {
                    "tool": "final_answer",
                    "args": {"answer": response}
                }
            }
            return json.dumps(fallback)
    
    return react_llm_wrapper

def main():
    print("🚀 ReAct Agent with Real LLM and Robust JSON Parsing\n")
    
    # Create the agent
    agent = ReActAgent()
    
    # Register tools
    agent.register_tool(add_numbers._tool)
    agent.register_tool(multiply_numbers._tool)
    
    print(f"📦 Registered tools: {list(agent.tools.keys())}\n")
    
    # Get the LLM wrapper
    llm = create_react_llm()
    
    # Test queries
    queries = [
        "What is 15 plus 27?",
        "Calculate 8 times 9",
        "I need to add 100 and 250, then multiply the result by 2"
    ]
    
    for query_idx, query in enumerate(queries[:1], 1):  # Start with just one query
        print(f"\n{'🌟'*30}")
        print(f"QUERY {query_idx}: {query}")
        print(f"{'🌟'*30}")
        
        try:
            result = agent.run_react(
                query=query,
                llm_callable=llm,
                max_steps=5  # Allow up to 5 steps
            )
            
            print(f"\n{'='*60}")
            print(f"🎯 FINAL ANSWER: {result}")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n📊 REACT PATTERN SUMMARY:")
    print("1. User asks a question")
    print("2. Agent THINKS about what to do")
    print("3. Agent takes an ACTION (uses a tool)")
    print("4. Agent OBSERVES the result")
    print("5. Agent repeats steps 2-4 until it has the answer")
    print("6. Agent provides FINAL ANSWER")

if __name__ == "__main__":
    main()