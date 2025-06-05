# tinyAgent

![tinyAgent Logo](static/images/tinyAgent_logo_v2.png)

Turn any Python function into an AI‑powered agent in just a few lines:

```python
from tinyagent import tool, ReactAgent

@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers together."""
    return a * b

@tool
def divide(a: float, b: float) -> float:
    """Divide the first number by the second number."""
    return a / b

agent = ReactAgent(tools=[multiply, divide])
result = agent.run("What is 12 times 5, then divided by 3?")
# → 20
```

That's it! The agent automatically:
- Understands it needs to perform multiple steps
- Calls `multiply(12, 5)` → gets 60
- Takes that result and calls `divide(60, 3)` → gets 20
- Returns the final answer

## Why tinyAgent?

- **Zero boilerplate** – Just decorate functions with `@tool`
- **Automatic reasoning** – Agent figures out which tools to use and in what order
- **Built-in LLM** – Works out of the box with OpenRouter
- **Type safe** – Full type hints and validation
- **Production ready** – Error handling, retries, and observability

## Installation

```bash
pip install tiny_agent_os

# With observability (recommended)
pip install "tiny_agent_os[traceboard]"

# With all features
pip install "tiny_agent_os[rag,traceboard]"
```

## Quick Setup

1. Get configuration files:
```bash
# Download config.yml
wget https://raw.githubusercontent.com/alchemiststudiosDOTai/tinyAgent/0.72/config.yml

# Download .env template
wget https://raw.githubusercontent.com/alchemiststudiosDOTai/tinyAgent/0.72/.envexample -O .env
```

2. Add your API key to `.env`:
```
OPENROUTER_API_KEY=your_key_here
```

Get your key at [openrouter.ai](https://openrouter.ai)

## More Examples

### Multi-step reasoning
```python
from tinyagent import tool, ReactAgent

@tool
def calculate_percentage(value: float, percentage: float) -> float:
    """Calculate what percentage of a value is."""
    return value * (percentage / 100)

@tool
def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b

agent = ReactAgent(tools=[calculate_percentage, subtract])
result = agent.run("If I have 15 apples and give away 40%, how many are left?")
print(result)  # → "You have 9 apples left."
```

Behind the scenes:
1. Agent calculates 40% of 15 → 6
2. Subtracts 6 from 15 → 9
3. Returns a natural language answer

## Key Features

### ReactAgent (Recommended)
- **Multi-step reasoning** - Breaks down complex problems automatically
- **Clean API** - Simple, ergonomic interface
- **Error handling** - Built-in retry logic and graceful failures
- **Observability** - Optional tracing to see what the agent is doing
- **Customizable prompts** - Pass custom system prompts via `system_prompt` parameter

### Tools Philosophy
Every function can be a tool. Keep them:
- **Atomic** - Do one thing well
- **Typed** - Use type hints for parameters
- **Documented** - Docstrings help the LLM understand usage

## Documentation

- [Complete Examples](examples/)
- [Tool Creation Guide](documentation/agentsarefunction.md)
- [ReactAgent Pattern](notes/react_agent_implementation.md)
- [Observability](documentation/observability.md)
- [RAG Support](documentation/rag.md)

## Status

**BETA** - Actively developed and used in production. Breaking changes possible until v1.0.

Found a bug? Have a feature request? [Open an issue](https://github.com/alchemiststudiosDOTai/tinyAgent/issues)!

## License

**Business Source License 1.1**
- ✅ Free for individuals and small businesses (< $1M revenue)
- 📧 Enterprise license required for larger companies

Contact: [info@alchemiststudios.ai](mailto:info@alchemiststudios.ai)

---

Made by [@tunahorse21](https://x.com/tunahorse21) | [alchemiststudios.ai](https://alchemiststudios.ai)