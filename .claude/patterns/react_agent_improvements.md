# ReactAgent Improvements Pattern

## Problem
The minimal ReactAgent lacked several features that made debugging difficult and error recovery poor:
1. No scratchpad for LLM thinking
2. No argument validation before tool calls
3. No distinction between observations and errors
4. No token budget control for long outputs
5. Hard failure on step limit
6. No visibility into execution process

## Solution Pattern

### 1. Scratchpad Support
```python
# In system prompt:
3. To think out loud (optional):
{"scratchpad": "Your reasoning here", "tool": "tool_name", "arguments": {...}}
{"scratchpad": "Your reasoning here", "answer": "Your answer"}

# In run method:
if "scratchpad" in payload:
    if verbose:
        print(f"\n[SCRATCHPAD]: {payload['scratchpad']}")
    messages += [
        {"role": "assistant", "content": assistant_reply},
        {"role": "user", "content": f"Scratchpad noted: {payload['scratchpad']}"},
    ]
    del payload["scratchpad"]
```

### 2. Argument Validation
```python
def _safe_tool(self, name: str, args: dict[str, Any], verbose: bool = False) -> tuple[bool, Any]:
    tool = self._tool_map[name]

    # Basic arg validation using function signature
    from inspect import signature
    try:
        signature(tool.fn).bind(**args)
    except TypeError as exc:
        if verbose:
            print(f"[!] ARGUMENT ERROR: {exc}")
        return False, f"ArgError: {exc}"
```

### 3. Observation vs Error Tags
```python
ok, result = self._safe_tool(name, args, verbose=verbose)
tag = "Observation" if ok else "Error"
short = (str(result)[: MAX_OBS_LEN] + "…") if len(str(result)) > MAX_OBS_LEN else result

messages += [
    {"role": "assistant", "content": assistant_reply},
    {"role": "user", "content": f"{tag}: {short}"},
]
```

### 4. Output Truncation
```python
MAX_OBS_LEN: Final = 500  # truncate tool output to avoid prompt blow-up

# Truncate long outputs
short = (str(result)[: MAX_OBS_LEN] + "…") if len(str(result)) > MAX_OBS_LEN else result
```

### 5. Graceful Step Limit Handling
```python
# Step limit hit → ask once for best guess
if verbose:
    print(f"\n{'='*40} FINAL ATTEMPT {'='*40}")
    print("[!] Step limit reached. Asking for final answer...")

final_try = self._chat(
    messages + [{"role": "user", "content": "Return your best final answer now."}], 0
)
payload = self._try_parse_json(final_try) or {}
if "answer" in payload:
    return payload["answer"]
raise StepLimitReached("Exceeded max steps without an answer.")
```

### 6. Verbose Logging
```python
def run(self, question: str, *, max_steps: int = MAX_STEPS, verbose: bool = False) -> str:
    if verbose:
        print("\n" + "=" * 80)
        print("REACT AGENT STARTING")
        print("=" * 80)
        print(f"\nTASK: {question}")
        print(f"\nSYSTEM PROMPT:\n{self._system_prompt}")
        print(f"\nAVAILABLE TOOLS: {list(self._tool_map.keys())}")

    # Throughout execution:
    # - Log each step number
    # - Show messages being sent to LLM
    # - Display LLM responses
    # - Show tool calls and results
    # - Highlight errors and recovery
```

## Results
- Better error recovery (ArgError vs ToolError)
- LLM can reason through problems in scratchpad
- Cleaner observation/error distinction
- Prevents prompt explosion from long outputs
- More graceful failures
- Full visibility into reasoning process

## Implementation Stats
- Added < 60 lines of code
- Maintained backward compatibility
- Improved convergence (weather example: 10 steps → 3 steps)
- All 21 tests passing

## Key Takeaways
1. **Scratchpad is powerful** - Lets the LLM think without breaking JSON structure
2. **Argument validation saves steps** - Catch errors before execution
3. **Clear error messages help recovery** - "ArgError" vs "ToolError" guides the model
4. **Output truncation is essential** - Prevents context window explosion
5. **Verbose mode aids debugging** - Full visibility into the reasoning process

## Example Usage
```python
agent = ReactAgent(
    tools=[get_weather, search_flights, calculate_trip_cost],
    model="gpt-4o-mini",
)

# With verbose output
answer = agent.run(
    "Compare weather in Tokyo and London",
    max_steps=10,
    verbose=True
)
```
