---

# tinyAgent 🤖

![tinyAgent Logo](static/images/tinyAgent_logo_v2.png)

## ⚠️ Important Notice - Framework Evolution

**ReactAgent is now the recommended approach for new projects.** Going forward, ReactAgent will be the primary focus for development and new features. The simple agent (`tiny_agent`) and tinyChain will remain available for backward compatibility, but won't receive active development or new features.

**Why ReactAgent?**
- ✅ **Better reasoning** - Multi-step thinking with explicit thought processes
- ✅ **More reliable** - Built-in error handling and retry logic
- ✅ **Cleaner API** - No need to pass `llm_callable=get_llm()` anymore
- ✅ **Future-proof** - All new features will be added here first

---

# Why tinyAgent?

Turn any Python function into an AI‑powered agent in three lines:

```python
from tinyagent.decorators import tool
from tinyagent.react.react_agent import ReactAgent

@tool                  # 1️⃣  function → tool
def calculate_percentage(value: float, percentage: float) -> float:
    """Calculate what percentage of a value is (e.g., 40% of 15)."""
    return value * (percentage / 100)

@tool
def subtract_numbers(number1: float, number2: float) -> float:
    """Subtract the second number from the first number."""
    return number1 - number2

agent = ReactAgent()                        # 2️⃣  tool → agent (LLM auto-configured!)
agent.register_tool(calculate_percentage._tool)
agent.register_tool(subtract_numbers._tool)
result = agent.run_react("If I have 15 apples and give away 40%, how many do I have left?")     # 3️⃣  multi-step reasoning
print(result)
# → "You have 9 apples left."
```

**Real Output:**
```
Thought: I need to calculate 40% of 15 apples first, then subtract that from the original 15 apples.

Action: calculate_percentage
Action Input: {"value": 15, "percentage": 40}

RESULT: 6.0

Thought: Now I need to subtract 6 from 15 to find out how many apples are left.

Action: subtract_numbers
Action Input: {"number1": 15, "number2": 6.0}

RESULT: 9.0

Action: final_answer
Action Input: {"answer": "You have 9 apples left."}

*** FINAL ANSWER CALLED ***
Answer: You have 9 apples left.

FINAL ANSWER: You have 9 apples left.
```

- **Zero boilerplate** – just a decorator and register tools.
- **Built‑in LLM orchestration** – validation, JSON I/O, retry, fallback.
- **ReAct Pattern** – Advanced reasoning + acting pattern for complex multi-step tasks.
- **Scales as you grow** – add more tools without rewrites.

**Made by (x) [@tunahorse21](https://x.com/tunahorse21) | A product of [alchemiststudios.ai](https://alchemiststudios.ai)**

---

## Heads Up

tinyAgent is in **BETA** until V1. It's working but still evolving! I can't guarantee it's 100% bug-free, but I'm actively improving it whenever I can between my day job and business.  
Found something that could be better? Show off your skills and open an issue with a fix: I'd genuinely appreciate it!

---

## Overview

tinyAgent is a streamlined framework for building powerful, LLM-powered agents that solve complex tasks through tool execution, orchestration, and dynamic capability creation. Convert any Python function into a useful tool and then into an agent with minimal configuration, unlocking a world of scalable, modular possibilities.

---

## Installation & Setup

### 1. Install the Package

```bash
# Basic installation
pip install tiny_agent_os

# With observability features (recommended)
pip install "tiny_agent_os[traceboard]"

# With all features (RAG + observability)
pip install "tiny_agent_os[rag,traceboard]"
```

### 2. Get the Configuration Files

After installation, you'll need two configuration files:

```bash
# Create a basic config.yml
python -m tinyagent.config init

# Or download the example config directly
wget https://raw.githubusercontent.com/alchemiststudiosDOTai/tinyAgent/v0.65/config.yml
```

Create a `.env` file with your API keys:

```bash
# Download the example .env file
wget https://raw.githubusercontent.com/alchemiststudiosDOTai/tinyAgent/v0.65/.envexample -O .env

# Edit with your API keys
nano .env  # or use any text editor
```

### 3. Quick Start Example (ReactAgent - Recommended!)

```python
from tinyagent.decorators import tool
from tinyagent.react.react_agent import ReactAgent

# Define a tool
@tool
def add(a: int, b: int) -> int:
    return a + b

# Create a ReactAgent (LLM automatically configured!)
agent = ReactAgent()
agent.register_tool(add._tool)

# Run it with reasoning!
result = agent.run_react("add 40 and 2")
print(result)  # → Shows the reasoning process and final answer: 42
```

### 4. ReactAgent Pattern (RECOMMENDED!) - Complete Working Example

Here's the complete working example from `examples/react_phase2.py`:

```python
#!/usr/bin/env python3
"""
ReactAgent Example - README Demo

This example demonstrates the ReactAgent with the same tools and query
used in the README, showing multi-step reasoning with atomic tools.
"""

from tinyagent.decorators import tool
from tinyagent.react.react_agent import ReactAgent

# Create atomic tools following tinyAgent philosophy
@tool
def calculate_percentage(value: float, percentage: float) -> float:
    """Calculate what percentage of a value is (e.g., 40% of 15)."""
    result = value * (percentage / 100)
    print(f"\n[Tool Execution] calculate_percentage({value}, {percentage}%) = {result}")
    return result

@tool
def subtract_numbers(number1: float, number2: float) -> float:
    """Subtract the second number from the first number. Use parameters: number1 (first number), number2 (second number). Returns number1 - number2."""
    result = number1 - number2
    print(f"\n[Tool Execution] subtract_numbers({number1} - {number2}) = {result}")
    return result

@tool
def add_numbers(number1: float, number2: float) -> float:
    """Add two numbers together. Use parameters: number1 (first number), number2 (second number). Returns number1 + number2."""
    result = number1 + number2
    print(f"\n[Tool Execution] add_numbers({number1} + {number2}) = {result}")
    return result

def main():
    print("ReactAgent README Example - Apple Calculation\n")
    print("This demonstrates the exact example from the README:")
    print("'If I have 15 apples and give away 40%, how many do I have left?'\n")
    
    # Create ReactAgent (LLM automatically configured!)
    agent = ReactAgent()
    
    # Register our atomic tools
    agent.register_tool(calculate_percentage._tool)
    agent.register_tool(subtract_numbers._tool)
    
    print(f"Registered tools:")
    for tool in agent.tools:
        print(f"  - {tool.name}: {tool.description}")
    print()
    
    # The exact query from the README
    query = "If I have 15 apples and give away 40%, how many do I have left?"
    
    print(f"Query: {query}\n")
    print("Starting ReactAgent reasoning process...\n")
    print("="*60)
    
    try:
        # Run with reasoning steps
        result = agent.run_react(query, max_steps=5)
        
        print("="*60)
        print(f"\nFINAL ANSWER: {result}")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
```

**Key Features:**
- ✅ **Automatic tool discovery** - Framework tells LLM about available tools
- ✅ **No "Unknown tool" errors** - LLM uses exact tool names from registration  
- ✅ **Zero configuration** - Just register tools and run
- ✅ **Built-in LLM** - Uses your config.yml settings automatically
- ✅ **Multi-step reasoning** - Handles complex queries requiring multiple tool calls
- ✅ **Clean final answers** - Built-in `final_answer` tool for clean termination
- ✅ **Exception-based flow** - Reliable completion mechanism inspired by SmolAgent

### 5. Legacy Simple Agent (Still Supported)

For simple use cases, the original pattern still works:

```python
from tinyagent.decorators import tool
from tinyagent.agent import tiny_agent

@tool
def add(a: int, b: int) -> int:
    return a + b

agent = tiny_agent(tools=[add])
result = agent.run("add 40 and 2")
print(result)  # → 42
```

---

## Post-Installation Configuration

After installing (either via pip or from source), remember to configure your environment and `.env` files with relevant API keys from https://openrouter.ai

Both the config.yml and env work out of the box with a openrouter API, you can use any openai API, and the config has an example of a local LLM.
The /documentation folder has more details and is being updated.

## Features

- **Modular Design:** Easily convert any function into a tool.
- **ReactAgent Pattern:** Built-in support for Reasoning + Acting pattern for complex multi-step reasoning tasks.
- **Flexible Agent Options:** Use ReactAgent (recommended) or the simple orchestrator.
- **Robust Error Handling:** Improved debugging with custom exceptions and JSON parsing.
- **Structured Output:** Enforce JSON formats for consistent outputs.
- **Clean Final Answers:** Exception-based flow control inspired by SmolAgent for reliable completion.
- **Comprehensive Observability:** Built-in OpenTelemetry tracing with multiple exporters (console, OTLP, SQLite) and a web-based trace viewer.

---

## Acknowledgments & Inspirations

- **my wife**
- [HuggingFace SmoLAgents](https://github.com/huggingface/smolagents)
- [Aider-AI](https://github.com/Aider-AI/aider)
- And many other open-source contributors!

---

## Learn More

- [Functions as Tools](documentation/agentsarefunction.md)
- [ReactAgent Pattern Guide](documentation/react_pattern.md)
- [tinyChain Overview](documentation/tiny_chain_overview.md) *(Note: tinyChain will be sunset soon in favor of ReactAgent pattern due to better performance and stability. Existing code will continue to work but won't receive updates.)*
- [RAG](documentation/rag.md)
- [Observability](documentation/observability.md)

---

---

## Contact

For questions, suggestions, or business inquiries:

- **Email**: [info@alchemiststudios.ai](mailto:info@alchemiststudios.ai)
- **X**: [@tunahorse21](https://x.com/tunahorse21)
- **Website**: [alchemiststudios.ai](https://alchemiststudios.ai)

---

## License

**Business Source License 1.1 (BSL)**
This project is licensed under the Business Source License 1.1. It is **free for individuals and small businesses** (with annual revenues under $1M).
For commercial use by larger businesses, an enterprise license is required.
For licensing or usage inquiries, please contact: [info@alchemiststudios.ai](mailto:info@alchemiststudios.ai)

---
