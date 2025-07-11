# TinyCodeAgent Schema Handling Pattern

## Problem
When tools return dicts, LLMs often guess wrong field names, leading to KeyErrors and exhausted step limits.

## Solution Pattern

### 1. Enhanced Tool Docstrings
```python
@tool
def get_weather(city: str) -> dict:
    """Get current weather for a city.

    Returns dict with keys:
    - temp: int (temperature in Celsius)
    - condition: str (e.g. 'Partly cloudy', 'Sunny', 'Rainy')
    - humidity: int (percentage 0-100)

    Example:
        get_weather('Tokyo')
        # Returns: {"temp": 22, "condition": "Partly cloudy", "humidity": 65}
    """
```

### 2. Specific Error Handling
```python
except KeyError as e:
    error_msg = f"KeyError: {e}. "
    if "get_weather" in code:
        error_msg += "Note: get_weather() returns dict with keys: 'temp', 'condition', 'humidity'"
    messages += [{"role": "assistant", "content": reply},
                 {"role": "user", "content": error_msg}]
```

### 3. System Prompt Extensions
```python
agent = TinyCodeAgent(
    tools=[...],
    system_suffix="Example: get_weather('Tokyo') returns {'temp': 22, ...}"
)
```

## Results
- Model recovers from KeyError in 1-2 attempts instead of exhausting step limit
- Clear schema in docstring prevents most errors
- Specific error messages guide quick correction

## Example Implementation
See: tinyagent/code_agent.py lines 283-296, tinyagent/examples/code_agent_demo.py

## Key Takeaway
Give LLMs unambiguous field names upfront (via docstrings) rather than letting them guess.
