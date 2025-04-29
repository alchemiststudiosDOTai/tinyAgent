---

# tinyAgent 🤖

![tinyAgent Logo](static/images/tinyAgent_logo_v2.png)

```
   __  .__                _____                         __
_/  |_|__| ____ ___.__. /  _  \    ____   ____   _____/  |_
\   __\  |/    <   |  |/  /_\  \  / ___\_/ __ \ /    \   __\
 |  | |  |   |  \___  /    |    \/ /_/  >  ___/|   |  \  |
 |__| |__|___|  / ____\____|__  /\___  / \___  >___|  /__|
              \/\/            \/\/_____/      \/     \/
```

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
- **Scales as you grow** – add more tools or plug into tiny_chain without rewrites.

# Why tiny_chain?

Handle multi‑step questions with automatic tool planning in <10 lines.

```python
from tinyagent.factory.tiny_chain import tiny_chain
from tinyagent.tools.duckduckgo_search import get_tool as search
from tinyagent.tools.custom_text_browser import get_tool as browser
from tinyagent.decorators import tool

@tool
def summarize(text: str) -> str:            # simple LLM summariser
    return "TL;DR → " + text[:200]

chain = tiny_chain.get_instance(tools=[search(), browser(), summarize._tool])
print(chain.run("Find current US import tariffs and summarise"))
# → bullet‑point answer pulled from official sources
```

- **One entry point** – submit a natural‑language task, get JSON results.
- **LLM triage agent** – chooses the best tool chain (search → browser → summarise).
- **Robust fallback** – if planning fails, it just tries every tool once.

**Made by (x) [@tunahorse21](https://x.com/tunahorse21) | A product of [alchemiststudios.ai](https://alchemiststudios.ai)**

---

## Heads Up

tinyAgent is in **BETA** until V1. It's working but still evolving! I can't guarantee it's 100% bug-free, but I'm actively improving it whenever I can between my day job and business.  
Found something that could be better? Show off your skills and open an issue with a fix: I'd genuinely appreciate it!

---

## Overview

tinyAgent is a streamlined framework for building powerful, LLM-powered agents that solve complex tasks through tool execution, orchestration, and dynamic capability creation. Convert any Python function into a useful tool and then into an agent with minimal configuration, unlocking a world of scalable, modular possibilities.

---

## Installation

### Via pip (Recommended)

```bash
pip install tiny_agent_os
```

### RAG (Retrieval-Augmented Generation) Optional Dependencies

- For local embeddings (sentence-transformers):
  ```bash
  pip install tiny_agent_os[rag-local]
  ```
- For OpenAI API embeddings:
  ```bash
  pip install tiny_agent_os[rag-api]
  ```
- For both local and API embedding support:
  ```bash
  pip install tiny_agent_os[rag]
  ```

---

## Post-Installation Configuration for Pip Users

After installing via `pip`, you'll need to provide your own configuration files. For convenience, you can download the defaults directly:

---

### Download the Configuration File (`config.yml`)

**Using `wget`:**

```bash
wget https://raw.githubusercontent.com/alchemiststudiosDOTai/tinyAgent/v0.65/config.yml
```

---

### Download the Environment File (`.env`)

Download the example environment file and rename it to `.env`:

**Using `wget`:**

```bash
wget https://raw.githubusercontent.com/alchemiststudiosDOTai/tinyAgent/v0.65/.envexample -O .env
```

> **Note:** Be sure to edit the `.env` file with your actual API keys and any other required variables.

---

### Cloning for Development

```bash
git clone https://github.com/alchemiststudiosDOTai/tinyAgent.git
cd tinyAgent
```

---

## Post-Installation Configuration

After installing (either via pip or from source), remember to configure your environment and `.env` files with relevant API keys from https://openrouter.ai

Both the config.yml and env work out of the box with a openrouter API, you can use any openai API, and the config has an example of a local LLM.
The /documentation folder has more details and is being updated.

## Learn More

- [Functions as Tools](documentation/agentsarefunction.md)
- [tinyChain Overview](documentation/tiny_chain_overview.md)
- [Examples](documentation/agents.md)

---
