---

# tinyAgent 🤖

![tinyAgent Logo](static/images/tinyAgent_logo_v2.png)


# Why tinyAgent?

Turn any Python function into an AI‑powered agent in three lines:

```python
from tinyagent.decorators import tool
from tinyagent.agent import tiny_agent

@tool                  # 1️⃣  function → tool
def add(a: int, b: int) -> int:
    return a + b

agent = tiny_agent(tools=[add])             # 2️⃣  tool → agent
print(agent.run("add 40 and 2"))           # 3️⃣  natural‑language call
# → 42
```

- **Zero boilerplate** – just a decorator.
- **Built‑in LLM orchestration** – validation, JSON I/O, retry, fallback.
- **ReAct Pattern Support** – Advanced reasoning + acting pattern for complex multi-step tasks.
- **Scales as you grow** – add more tools or plug into tiny_chain without rewrites.


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

### 3. Quick Start Example

```python
from tinyagent.decorators import tool
from tinyagent.agent import tiny_agent
from tinyagent.observability.tracer import configure_tracing  # For tracing support

# Define a tool
@tool
def add(a: int, b: int) -> int:
    return a + b

# Enable tracing (optional)
configure_tracing()  # This reads your config.yml

# Create an agent (with tracing enabled)
agent = tiny_agent(tools=[add], trace_this_agent=True)

# Run it!
result = agent.run("add 40 and 2")
print(result)  # → 42
```

### 4. ReAct Pattern Example (NEW!)

For complex multi-step reasoning tasks, use the ReAct agent:

```python
from tinyagent.react.react_agent import ReActAgent
from tinyagent.decorators import tool
from tinyagent.agent import get_llm

# Define tools
@tool
def calculate(expression: str) -> float:
    """Evaluate a mathematical expression."""
    return eval(expression)

# Create ReAct agent
agent = ReActAgent()
agent.register_tool(calculate._tool)

# Run with reasoning steps
result = agent.run_react(
    query="If I have 15 apples and give away 40%, how many do I have left?",
    llm_callable=get_llm(),
    max_steps=3
)
print(result)  # → "You have 9 apples left"
```

---

## Post-Installation Configuration

After installing (either via pip or from source), remember to configure your environment and `.env` files with relevant API keys from https://openrouter.ai

Both the config.yml and env work out of the box with a openrouter API, you can use any openai API, and the config has an example of a local LLM.
The /documentation folder has more details and is being updated.

## Features

- **Modular Design:** Easily convert any function into a tool.
- **Flexible Agent Options:** Use the simple orchestrator or advanced `AgentFactory`.
- **ReAct Pattern:** Built-in support for Reasoning + Acting pattern for complex multi-step reasoning tasks.
- **Robust Error Handling:** Improved debugging with custom exceptions and JSON parsing.
- **Structured Output:** Enforce JSON formats for consistent outputs.
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
- [ReAct Pattern Guide](documentation/react_pattern.md)
- [tinyChain Overview](documentation/tiny_chain_overview.md) *(Note: tinyChain will be sunset soon in favor of ReAct pattern due to better performance and stability. Existing code will continue to work but won't receive updates.)*
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
