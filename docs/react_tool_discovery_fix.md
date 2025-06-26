# ReAct Tool Discovery Fix

## Issue
Users were getting "ValueError: Unknown tool: calculator" when using the ReAct agent example from the README. The LLM would guess tool names that didn't match the registered tools.

## Root Cause
The ReAct agent's `_build_prompt` method was not including information about available tools in the prompt sent to the LLM. This meant:
- LLM had no knowledge of what tools were available
- LLM would guess tool names based on context (e.g., "calculator" instead of "calculate")
- Framework would throw "Unknown tool" errors when LLM used incorrect names

## Solution
Modified `src/tinyagent/react/react_agent.py` to automatically include tool information in prompts:

```python
# Add available tools information
if self.tools:
    instructions += f"\n\nAVAILABLE TOOLS:\n"
    for tool_name, tool in self.tools.items():
        instructions += f"- {tool_name}: {tool.description or 'No description available'}\n"
```

## Impact
- ✅ No more "Unknown tool" errors
- ✅ LLM uses exact tool names from registration
- ✅ Zero configuration required from users
- ✅ Framework handles tool discovery automatically

## Files Modified
- `src/tinyagent/react/react_agent.py` - Added automatic tool discovery
- `README.md` - Updated ReAct example with better documentation
- `examples/react_fixed_example.py` - Working example with real API calls
- `examples/react_full_test.py` - Full test with mock responses  
- `examples/react_test_prompt.py` - Prompt building demonstration

## Test Results
Confirmed working with real OpenRouter API calls. LLM correctly uses registered tool names and successfully completes multi-step reasoning tasks.

## Date
January 2025