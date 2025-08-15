# Advanced Usage Examples

This document provides examples of advanced TinyAgent usage patterns and customizations.

## Custom Tool Implementation

```python
from tinyagent import tool
from typing import Dict, Any
import requests

@tool
def api_caller(endpoint: str, method: str = "GET", data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make HTTP requests to external APIs."""
    try:
        response = requests.request(method, endpoint, json=data, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# Usage with ReactAgent
from tinyagent import ReactAgent
agent = ReactAgent(tools=[api_caller])
```

## Custom Agent with Extended Prompts

```python
from tinyagent import ReactAgent
from tinyagent.prompt import SYSTEM

class CustomAgent(ReactAgent):
    def __post_init__(self):
        # Call parent initialization
        super().__post_init__()

        # Extend system prompt
        custom_instructions = "\n\nSpecial instructions: Always double-check calculations."
        self._system_prompt += custom_instructions

# Usage
agent = CustomAgent(tools=[calculator_tool])
```

## Multi-Agent Coordination

```python
from tinyagent import ReactAgent, tool

@tool
def math_agent_task(problem: str) -> str:
    """Delegate math problems to a specialized agent."""
    math_agent = ReactAgent(tools=[calculator])
    return math_agent.run(problem)

@tool
def web_agent_task(query: str) -> str:
    """Delegate web search to a specialized agent."""
    web_agent = ReactAgent(tools=[web_search])
    return web_agent.run(query)

# Main agent that coordinates sub-agents
main_agent = ReactAgent(tools=[math_agent_task, web_agent_task])
result = main_agent.run("Calculate 2+2 and find the capital of Japan")
```

## Custom PythonExecutor Configuration

```python
from tinyagent import TinyCodeAgent

# Allow additional imports in code execution
agent = TinyCodeAgent(
    tools=[data_processing_tool],
    extra_imports=["json", "csv", "datetime"]
)

# The agent can now use these imports in generated code:
# ```python
# import json
# import csv
# from datetime import datetime
# # ... rest of code
# ```
```

## Streaming Response Processing

```python
from tinyagent import ReactAgent
import asyncio

class StreamingAgent(ReactAgent):
    async def run_async(self, question: str, *, max_steps: int = 10):
        """Run agent with async streaming of thoughts."""
        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": question},
        ]

        for step in range(max_steps):
            # Stream each step
            yield f"Step {step + 1}: Processing..."

            assistant_reply = self._chat(messages, 0.0)
            yield f"LLM Response: {assistant_reply}"

            # Process response (simplified)
            if '"answer"' in assistant_reply:
                import json
                payload = json.loads(assistant_reply)
                yield f"Final Answer: {payload['answer']}"
                return

            messages.append({"role": "assistant", "content": assistant_reply})
            messages.append({"role": "user", "content": "Continue processing"})

# Usage
async def main():
    agent = StreamingAgent(tools=[calculator])
    async for update in agent.run_async("Calculate 5 + 3"):
        print(update)
```

## Tool with Complex Return Types

```python
from tinyagent import tool
from dataclasses import dataclass
from typing import List

@dataclass
class WeatherReport:
    city: str
    temperature: float
    conditions: str
    humidity: int

@tool
def get_detailed_weather(city: str) -> str:
    """Get detailed weather information."""
    # In practice, this would call a weather API
    report = WeatherReport(
        city=city,
        temperature=75.5,
        conditions="Partly Cloudy",
        humidity=65
    )

    # Convert to string for LLM consumption
    return (f"Weather in {report.city}: {report.temperature}°F, "
            f"{report.conditions}, {report.humidity}% humidity")

# Usage
from tinyagent import ReactAgent
agent = ReactAgent(tools=[get_detailed_weather])
result = agent.run("What's the weather in Boston?")
```

## Custom Error Handling and Retry Logic

```python
from tinyagent import ReactAgent
from tinyagent.agent import StepLimitReached
import time

class ResilientAgent(ReactAgent):
    def run_with_backoff(self, question: str, *, max_retries: int = 3):
        """Run agent with exponential backoff on failures."""
        for attempt in range(max_retries):
            try:
                return self.run(question)
            except StepLimitReached:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    time.sleep(wait_time)
                    continue
                raise
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                raise

# Usage
agent = ResilientAgent(tools=[web_search])
result = agent.run_with_backoff("Latest news about AI")
```

## Integration with External Systems

```python
from tinyagent import tool
import sqlite3

@tool
def query_database(sql: str, db_path: str = "data.db") -> str:
    """Execute SQL queries against a database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        conn.close()
        return str(results)
    except Exception as e:
        return f"Database error: {e}"

# Usage
from tinyagent import ReactAgent
agent = ReactAgent(tools=[query_database])

# Agent can now interact with databases:
# "Query the users table for all users in New York"
```

## Custom Tool Validation

```python
from tinyagent import tool
from functools import wraps

def validate_inputs(func):
    """Decorator to add input validation to tools."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Add validation logic here
        if 'amount' in kwargs and kwargs['amount'] < 0:
            raise ValueError("Amount must be positive")
        return func(*args, **kwargs)
    return wrapper

@tool
@validate_inputs
def process_payment(amount: float, account: str) -> str:
    """Process a payment transaction."""
    # Payment processing logic here
    return f"Processed ${amount} payment to {account}"

# Usage
from tinyagent import ReactAgent
agent = ReactAgent(tools=[process_payment])
```

These advanced examples demonstrate the extensibility and power of TinyAgent. They show how to customize agents, implement complex tools, and integrate with external systems while maintaining the core ReAct pattern.
